"""FastAPI REST API bridge for Digital Landfill.

Acts as the single point of communication between the Google AI Studio React
frontend and the local Python Digital Landfill intelligence modules.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any, Sequence

# Ensure workspace root is in sys.path so src modules can be imported
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.duplicates import DuplicateReport, find_duplicates
from src.metrics import summarize
from src.models import FileRecord, format_size
from src.qwen_client import QwenConfig, check_qwen_health
from src.qwen_service import (
    QwenService,
    build_grounded_scan_context,
    sanitize_evidence,
)
from src.recommendations import (
    Recommendation,
    RecommendationReport,
    generate_recommendations,
)
from src.scanner import scan_folder
from src.waste import (
    CategoryDistribution,
    DuplicateWasteSummary,
    LargeFilesReport,
    RecoveryEstimate,
    StaleFilesReport,
    TempFilesReport,
    WasteScoreReport,
    calculate_waste_score,
    find_large_files,
    find_stale_files,
    find_temp_cache_files,
    get_storage_distribution,
    simulate_recovery,
    summarize_duplicate_waste,
)

DEPLOYMENT_MODE = os.getenv("DEPLOYMENT_MODE", "local").strip().lower()
IS_DEMO_MODE = DEPLOYMENT_MODE in ("demo", "cloud")
DEMO_DIR = os.getenv("DEMO_DIR", "test_waste_sample")

app = FastAPI(
    title="Digital Landfill API",
    description="Digital Waste Intelligence and Knowledge Recovery API",
    version="1.0.0",
)

# CORS configuration: support explicit FRONTEND_ORIGIN for production or localhost regex for local
frontend_origin_env = os.getenv("FRONTEND_ORIGIN", "").strip()
if frontend_origin_env:
    allowed_origins = [o.strip() for o in frontend_origin_env.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ---------------------------------------------------------------------------
# Backend In-Memory State & Thread Safety
# ---------------------------------------------------------------------------


class BackendState:
    """Thread-safe state container for active scan and waste intelligence."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.scanned_root: str | None = None
        self.root_name: str = "No folder selected"
        self.records: list[FileRecord] = []
        self.errors: list[str] = []
        self.duplicates: DuplicateReport | None = None
        self.dup_summary: DuplicateWasteSummary | None = None
        self.waste_score: WasteScoreReport | None = None
        self.cat_distribution: list[CategoryDistribution] = []
        self.large_report: LargeFilesReport | None = None
        self.stale_report: StaleFilesReport | None = None
        self.temp_report: TempFilesReport | None = None
        self.recovery: RecoveryEstimate | None = None
        self.recommendations: RecommendationReport | None = None
        self.qwen_analysis: str | None = None
        self.qwen_rec_explanations: dict[str, str] = {}
        self.chat_history: list[dict[str, str]] = []
        self.scanned_at: str = "—"
        self.large_threshold_mb: int = 100
        self.stale_days_threshold: int = 180


state = BackendState()


def _get_qwen_service() -> QwenService:
    config = QwenConfig.from_env()
    return QwenService(config)


def _recompute_intelligence_locked() -> None:
    """Recompute all analytical waste, duplicate, and recommendation layers.
    MUST be called while holding state.lock.
    """
    records = state.records
    if not records:
        state.duplicates = DuplicateReport()
        state.dup_summary = summarize_duplicate_waste(state.duplicates)
        state.cat_distribution = []
        state.large_report = LargeFilesReport(
            threshold_bytes=state.large_threshold_mb * 1024 * 1024,
            threshold_mb=float(state.large_threshold_mb),
            count=0,
            total_bytes=0,
            total_size_label="0 B",
            files=[],
        )
        state.stale_report = StaleFilesReport(
            days_threshold=state.stale_days_threshold,
            count=0,
            total_bytes=0,
            total_size_label="0 B",
            files=[],
        )
        state.temp_report = TempFilesReport(
            count=0,
            total_bytes=0,
            total_size_label="0 B",
            files=[],
        )
        state.waste_score = calculate_waste_score(records)
        state.recovery = simulate_recovery(records)
        state.recommendations = RecommendationReport()
        state.qwen_analysis = None
        state.qwen_rec_explanations.clear()
        return

    # Phase 2: Duplicates
    state.duplicates = find_duplicates(records)
    state.dup_summary = summarize_duplicate_waste(state.duplicates)

    # Phase 3: Waste Analytics
    large_bytes = state.large_threshold_mb * 1024 * 1024
    state.cat_distribution = get_storage_distribution(records)
    state.large_report = find_large_files(records, threshold_bytes=large_bytes)
    state.stale_report = find_stale_files(records, days_threshold=state.stale_days_threshold)
    state.temp_report = find_temp_cache_files(records)
    state.waste_score = calculate_waste_score(
        records=records,
        duplicate_report=state.duplicates,
        large_report=state.large_report,
        stale_report=state.stale_report,
        temp_report=state.temp_report,
    )
    state.recovery = simulate_recovery(
        records=records,
        duplicate_report=state.duplicates,
        temp_report=state.temp_report,
        stale_report=state.stale_report,
    )

    # Phase 4: Recommendations
    state.recommendations = generate_recommendations(
        records=records,
        duplicate_report=state.duplicates,
        large_report=state.large_report,
        stale_report=state.stale_report,
        temp_report=state.temp_report,
        large_threshold_bytes=large_bytes,
        stale_days_threshold=state.stale_days_threshold,
    )


# ---------------------------------------------------------------------------
# Data Serialization Helpers for React Frontend
# ---------------------------------------------------------------------------

CATEGORY_COLORS: dict[str, str] = {
    "Documents": "#38bdf8",
    "Images": "#a855f7",
    "Code": "#34d399",
    "Datasets": "#f59e0b",
    "Videos": "#f43f5e",
    "Other": "#94a3b8",
    "Audio": "#ec4899",
    "Archives": "#eab308",
    "Presentations": "#f97316",
    "Spreadsheets": "#10b981",
}


def _file_to_item(
    record: FileRecord,
    dup_map: dict[str, tuple[str, bool, str]],
    large_paths: set[str],
    stale_paths: set[str],
    temp_paths: set[str],
) -> dict[str, Any]:
    """Serialize FileRecord to React FileItem interface."""
    path_str = record.path
    is_dup, group_id, is_copy, sha256_val = False, None, False, ""
    if path_str in dup_map:
        group_id, is_copy, sha256_val = dup_map[path_str]
        is_dup = True

    is_large = path_str in large_paths
    is_stale = path_str in stale_paths
    is_temp = path_str in temp_paths

    status_str = "Active"
    waste_reason: str | None = None
    if is_dup:
        status_str = "Duplicate"
        waste_reason = "Exact SHA-256 duplicate (redundant copy)" if is_copy else "Exact SHA-256 duplicate (master)"
    elif is_temp:
        status_str = "Temporary"
        waste_reason = "Temporary / cache pattern match"
    elif is_stale:
        status_str = "Stale"
        waste_reason = f"Unmodified for > {state.stale_days_threshold} days"

    mtime_epoch = int(record.modified_timestamp * 1000) if record.modified_timestamp > 0 else 0
    now_epoch = int(time.time() * 1000)
    age_days = max(0, int((now_epoch - mtime_epoch) / (86400 * 1000))) if mtime_epoch > 0 else 0

    return {
        "id": f"f-{abs(hash(record.path))}",
        "name": record.name,
        "path": record.path,
        "category": record.category,
        "sizeBytes": record.size_bytes,
        "sizeFormatted": record.size_label,
        "modifiedAt": record.modified_at,
        "lastModifiedEpoch": mtime_epoch,
        "ageDays": age_days,
        "sha256": sha256_val,
        "isDuplicate": is_dup,
        "duplicateGroupId": group_id,
        "isDuplicateCopy": is_copy,
        "isLarge": is_large,
        "isStale": is_stale,
        "isTemp": is_temp,
        "wasteReason": waste_reason,
        "status": status_str,
    }


def _build_full_scan_data() -> dict[str, Any]:
    """Compile active state into complete ScanData object expected by React UI."""
    summary = summarize(state.records)
    total_files = summary.get("total_files", 0)
    total_size_bytes = summary.get("total_bytes", 0)
    total_size_formatted = summary.get("total_size_label", "0 B")

    dup_report = state.duplicates or DuplicateReport()
    dup_waste_bytes = dup_report.redundant_bytes
    dup_waste_formatted = dup_report.redundant_size_label

    recovery = state.recovery
    pot_recovery_bytes = recovery.tier3_full_review_bytes if recovery else 0
    pot_recovery_formatted = recovery.tier3_full_review_label if recovery else "0 B"

    waste_score_val = state.waste_score.score_value if state.waste_score else 0
    waste_indicator_val = state.waste_score.level if state.waste_score else "LOW"

    # Category distributions
    cat_items: list[dict[str, Any]] = []
    for cd in state.cat_distribution:
        cat_items.append(
            {
                "category": cd.category,
                "count": cd.file_count,
                "bytes": cd.total_bytes,
                "formatted": cd.total_size_label,
                "percentage": cd.storage_pct,
                "color": CATEGORY_COLORS.get(cd.category, "#94a3b8"),
            }
        )

    # Fast lookup sets
    dup_map: dict[str, tuple[str, bool, str]] = {}
    duplicate_groups_json: list[dict[str, Any]] = []

    for idx, g in enumerate(dup_report.groups, 1):
        g_id = f"dup-{idx}"
        for f_idx, f in enumerate(g.files):
            # First file is master copy (isDuplicateCopy=False), subsequent are copies
            is_copy = f_idx > 0
            dup_map[f.path] = (g_id, is_copy, g.sha256)

        g_files = [
            _file_to_item(f, dup_map, set(), set(), set())
            for f in g.files
        ]

        priority_str = "HIGH" if g.redundant_bytes >= 50 * 1024 * 1024 else "MEDIUM" if g.redundant_bytes >= 5 * 1024 * 1024 else "LOW"

        duplicate_groups_json.append(
            {
                "id": g_id,
                "sha256": g.sha256,
                "originalFileName": g.files[0].name if g.files else "Unknown",
                "fileSizeFormatted": format_size(g.size_bytes),
                "fileSizeBytes": g.size_bytes,
                "copyCount": g.file_count,
                "redundantSizeBytes": g.redundant_bytes,
                "redundantSizeFormatted": g.redundant_size_label,
                "priority": priority_str,
                "files": g_files,
            }
        )

    large_paths = {f.path for f in (state.large_report.files if state.large_report else [])}
    stale_paths = {f.path for f in (state.stale_report.files if state.stale_report else [])}
    temp_paths = {f.path for f in (state.temp_report.files if state.temp_report else [])}

    file_items = [
        _file_to_item(r, dup_map, large_paths, stale_paths, temp_paths)
        for r in state.records
    ]

    # Recommendations
    recommendations_json: list[dict[str, Any]] = []
    if state.recommendations:
        for r in state.recommendations.recommendations:
            # Candidate file IDs
            candidate_ids = [f"f-{abs(hash(p))}" for p in r.all_paths]
            recommendations_json.append(
                {
                    "id": r.id,
                    "priority": r.priority,
                    "title": r.title,
                    "affectedCopiesCount": max(1, len(r.all_paths)),
                    "potentialRecoveryBytes": r.estimated_recovery_bytes,
                    "potentialRecoveryFormatted": r.estimated_recovery_label,
                    "whyFlagged": r.reasons,
                    "evidenceConfidence": r.confidence,
                    "suggestedAction": r.suggested_action,
                    "category": r.category,
                    "candidateFileIds": candidate_ids,
                    "qwenExplanation": state.qwen_rec_explanations.get(
                        r.id,
                        f"Explanation available on demand: {r.impact_description}",
                    ),
                }
            )

    # Signals
    signals = {
        "duplicates": {
            "count": dup_report.duplicate_files,
            "storageBytes": dup_waste_bytes,
            "storageFormatted": dup_waste_formatted,
            "severity": "HIGH" if dup_waste_bytes > 50 * 1024 * 1024 else "MEDIUM" if dup_waste_bytes > 0 else "LOW",
            "description": f"{dup_report.group_count} duplicate groups with {dup_report.redundant_files} redundant copies.",
        },
        "largeFiles": {
            "count": state.large_report.count if state.large_report else 0,
            "storageBytes": state.large_report.total_bytes if state.large_report else 0,
            "storageFormatted": state.large_report.total_size_label if state.large_report else "0 B",
            "severity": "HIGH" if (state.large_report and state.large_report.count > 5) else "MEDIUM" if (state.large_report and state.large_report.count > 0) else "LOW",
            "description": f"Files exceeding {state.large_threshold_mb} MB threshold.",
        },
        "staleFiles": {
            "count": state.stale_report.count if state.stale_report else 0,
            "storageBytes": state.stale_report.total_bytes if state.stale_report else 0,
            "storageFormatted": state.stale_report.total_size_label if state.stale_report else "0 B",
            "severity": "MEDIUM" if (state.stale_report and state.stale_report.count > 0) else "LOW",
            "description": f"Files unmodified for over {state.stale_days_threshold} days.",
        },
        "tempFiles": {
            "count": state.temp_report.count if state.temp_report else 0,
            "storageBytes": state.temp_report.total_bytes if state.temp_report else 0,
            "storageFormatted": state.temp_report.total_size_label if state.temp_report else "0 B",
            "severity": "MEDIUM" if (state.temp_report and state.temp_report.count > 0) else "LOW",
            "description": "Transient cache, log, and backup candidate files.",
        },
    }

    return {
        "folderPath": state.scanned_root or "No folder selected",
        "root_name": state.root_name,
        "totalFiles": total_files,
        "totalSizeBytes": total_size_bytes,
        "totalSizeFormatted": total_size_formatted,
        "duplicateWasteBytes": dup_waste_bytes,
        "duplicateWasteFormatted": dup_waste_formatted,
        "potentialRecoveryBytes": pot_recovery_bytes,
        "potentialRecoveryFormatted": pot_recovery_formatted,
        "wasteIndicator": waste_indicator_val,
        "wasteScore": waste_score_val,
        "scannedAt": state.scanned_at,
        "categories": cat_items,
        "signals": signals,
        "files": file_items,
        "duplicateGroups": duplicate_groups_json,
        "recommendations": recommendations_json,
    }


# ---------------------------------------------------------------------------
# API Request Models
# ---------------------------------------------------------------------------


class ScanRequest(BaseModel):
    root_path: str = Field(..., description="Absolute local filesystem directory path to scan")
    skip_hidden: bool = Field(True, description="Whether to exclude hidden files and directories")
    max_files: int | None = Field(None, description="Optional safety limit on maximum files to scan")
    large_threshold_mb: int | None = Field(100, description="Threshold in MB for large file classification")
    stale_days_threshold: int | None = Field(180, description="Threshold in days for stale file classification")


class QwenAnalyzeRequest(BaseModel):
    enable_thinking: bool = Field(False, description="Enable chain-of-thought deep reasoning mode")


class QwenExplainRequest(BaseModel):
    recommendation_id: str = Field(..., description="ID of the recommendation to explain")
    enable_thinking: bool = Field(False, description="Enable chain-of-thought deep reasoning mode")


class QwenAskRequest(BaseModel):
    query: str = Field(..., description="User query to ask about the scanned dataset")
    chat_history: list[dict[str, str]] = Field(default_factory=list, description="Recent conversation turns")
    enable_thinking: bool = Field(False, description="Enable chain-of-thought deep reasoning mode")


class DeleteRequest(BaseModel):
    path: str = Field(..., description="Absolute file path to delete")
    expected_size: int = Field(..., description="Expected file size in bytes for pre-verification")
    expected_modified_at: str | None = Field(None, description="Optional expected modified date for pre-verification")
    confirmed: bool = Field(..., description="Explicit user confirmation flag")


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------


@app.on_event("startup")
def startup_event() -> None:
    """Initialize state on startup. In Demo/Cloud mode, auto-loads the demo dataset."""
    if IS_DEMO_MODE:
        demo_path = Path(DEMO_DIR).resolve()
        if not demo_path.exists():
            demo_path = Path("test_waste_sample").resolve()
        if demo_path.exists() and demo_path.is_dir():
            try:
                records, errors = scan_folder(demo_path)
                with state.lock:
                    state.scanned_root = str(demo_path)
                    state.root_name = f"{demo_path.name} (Cloud Demo Dataset)"
                    state.records = records
                    state.errors = errors
                    state.scanned_at = time.strftime("%Y-%m-%d %H:%M")
                    _recompute_intelligence_locked()
            except Exception as exc:
                print(f"[Startup Warning] Could not auto-load demo directory: {exc}")


@app.get("/api/health")
def get_health() -> dict[str, Any]:
    """Health check endpoint providing backend status, deployment mode, and TCET CoE Gateway health."""
    qwen_cfg = QwenConfig.from_env()
    is_qwen_ok, qwen_badge, qwen_msg = check_qwen_health(qwen_cfg)

    with state.lock:
        scanned = state.scanned_root is not None
        root = state.scanned_root
        total_f = len(state.records)

    return {
        "status": "healthy",
        "service": "Digital Landfill FastAPI Backend",
        "deployment_mode": "demo" if IS_DEMO_MODE else "local",
        "is_demo_mode": IS_DEMO_MODE,
        "has_active_scan": scanned,
        "scanned_root": root,
        "total_files": total_f,
        "demo_dir": DEMO_DIR if IS_DEMO_MODE else None,
        "qwen_gateway": {
            "status": "Connected" if is_qwen_ok else "Not Configured" if not qwen_cfg.api_key else "Offline",
            "badge": qwen_badge,
            "detail": qwen_msg,
            "model": qwen_cfg.model,
            "base_url": qwen_cfg.base_url,
        },
    }


@app.post("/api/scan")
def scan_directory(req: ScanRequest) -> dict[str, Any]:
    """Initiate local folder scan and update backend state."""
    raw_path = req.root_path.strip()
    if not raw_path:
        raise HTTPException(status_code=400, detail="A non-empty folder path must be provided.")

    target_path = Path(raw_path).expanduser().resolve()

    # DEMO / CLOUD MODE SECURITY RESTRICTION:
    # Do not allow arbitrary server filesystem access in cloud/demo deployment mode.
    if IS_DEMO_MODE:
        workspace_root = Path(".").resolve()
        demo_allowed_roots = [
            Path(DEMO_DIR).resolve(),
            (workspace_root / "test_waste_sample").resolve(),
            (workspace_root / "demo_data").resolve(),
        ]
        is_safe_demo_target = False
        for allowed_root in demo_allowed_roots:
            if allowed_root.exists():
                try:
                    target_path.relative_to(allowed_root)
                    is_safe_demo_target = True
                    break
                except ValueError:
                    if target_path == allowed_root:
                        is_safe_demo_target = True
                        break

        if not is_safe_demo_target:
            raise HTTPException(
                status_code=403,
                detail=(
                    f"Demo / Cloud Mode Security Restriction: Arbitrary server filesystem paths cannot be scanned. "
                    f"Please select the bundled demo fixture '{DEMO_DIR}'."
                ),
            )

    if not target_path.exists() or not target_path.is_dir():
        raise HTTPException(status_code=400, detail=f"The folder '{raw_path}' does not exist or is not a directory.")

    try:
        records, errors = scan_folder(
            target_path,
            skip_hidden=req.skip_hidden,
            max_files=req.max_files,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scanning failed: {exc}")

    with state.lock:
        state.scanned_root = str(target_path)
        state.root_name = (
            f"{target_path.name} (Demo Dataset)" if IS_DEMO_MODE else (target_path.name or str(target_path))
        )
        state.records = records
        state.errors = errors
        state.scanned_at = time.strftime("%Y-%m-%d %H:%M")
        if req.large_threshold_mb is not None:
            state.large_threshold_mb = req.large_threshold_mb
        if req.stale_days_threshold is not None:
            state.stale_days_threshold = req.stale_days_threshold

        _recompute_intelligence_locked()
        scan_payload = _build_full_scan_data()

    return {
        "status": "success",
        "message": f"Successfully scanned {len(records):,} files in '{target_path.name}'.",
        "errors_count": len(errors),
        "data": scan_payload,
    }


@app.get("/api/summary")
def get_summary() -> dict[str, Any]:
    """Retrieve top-level summary metrics. Always returns a valid root_name."""
    with state.lock:
        scan_data = _build_full_scan_data()

    return {
        "root_name": scan_data["root_name"],
        "folder_path": scan_data["folderPath"],
        "total_files": scan_data["totalFiles"],
        "total_size_bytes": scan_data["totalSizeBytes"],
        "total_size_label": scan_data["totalSizeFormatted"],
        "duplicate_waste_bytes": scan_data["duplicateWasteBytes"],
        "duplicate_waste_label": scan_data["duplicateWasteFormatted"],
        "potential_recovery_bytes": scan_data["potentialRecoveryBytes"],
        "potential_recovery_label": scan_data["potentialRecoveryFormatted"],
        "waste_score": scan_data["wasteScore"],
        "waste_indicator": scan_data["wasteIndicator"],
        "scanned_at": scan_data["scannedAt"],
        "categories": scan_data["categories"],
        "signals": scan_data["signals"],
    }


@app.get("/api/scan_data")
def get_scan_data() -> dict[str, Any]:
    """Retrieve full ScanData payload matching Google AI Studio React frontend model."""
    with state.lock:
        return _build_full_scan_data()


@app.get("/api/files")
def get_files(
    search: str | None = Query(None, description="Search term for name or path"),
    category: str | None = Query(None, description="Filter by file category"),
    status: str | None = Query(None, description="Filter by status: Duplicate, Stale, Temporary, Active"),
    is_duplicate: bool | None = Query(None, description="Filter by duplicate status"),
    is_stale: bool | None = Query(None, description="Filter by stale status"),
    is_temp: bool | None = Query(None, description="Filter by temporary status"),
    is_large: bool | None = Query(None, description="Filter by large file status"),
    limit: int = Query(1000, ge=1, le=50000, description="Max files to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> dict[str, Any]:
    """Retrieve filtered, paginated file inventory from the active scan."""
    with state.lock:
        full_data = _build_full_scan_data()

    files = full_data["files"]

    if category and category != "All":
        files = [f for f in files if f["category"].lower() == category.lower()]

    if status and status != "All":
        files = [f for f in files if f["status"].lower() == status.lower()]

    if is_duplicate is not None:
        files = [f for f in files if f["isDuplicate"] == is_duplicate]

    if is_stale is not None:
        files = [f for f in files if f["isStale"] == is_stale]

    if is_temp is not None:
        files = [f for f in files if f["isTemp"] == is_temp]

    if is_large is not None:
        files = [f for f in files if f["isLarge"] == is_large]

    if search and search.strip():
        q = search.strip().lower()
        files = [
            f for f in files
            if q in f["name"].lower() or q in f["path"].lower()
        ]

    total_matched = len(files)
    paginated = files[offset : offset + limit]

    return {
        "total": total_matched,
        "limit": limit,
        "offset": offset,
        "files": paginated,
    }


@app.get("/api/waste")
def get_waste() -> dict[str, Any]:
    """Retrieve detailed waste intelligence and recovery simulation."""
    with state.lock:
        scan_data = _build_full_scan_data()
        recovery = state.recovery
        waste_score = state.waste_score

    sim_tiers = []
    if recovery:
        sim_tiers = [
            {
                "tier": "Tier 1: Exact Duplicates",
                "label": recovery.tier1_exact_label,
                "bytes": recovery.tier1_exact_bytes,
                "files_count": recovery.exact_recoverable_files,
                "safety": "100% Identical Copies (Zero risk)",
            },
            {
                "tier": "Tier 2: Duplicates + Temp/Cache",
                "label": recovery.tier2_with_temp_label,
                "bytes": recovery.tier2_with_temp_bytes,
                "files_count": recovery.exact_recoverable_files + recovery.temp_cache_candidate_files,
                "safety": "Review Candidate (Heuristic Temporary)",
            },
            {
                "tier": "Tier 3: Full Review Pool",
                "label": recovery.tier3_full_review_label,
                "bytes": recovery.tier3_full_review_bytes,
                "files_count": recovery.exact_recoverable_files + recovery.temp_cache_candidate_files + recovery.stale_candidate_files,
                "safety": "Review Candidate (Age > threshold)",
            },
        ]

    return {
        "storage_distribution": scan_data["categories"],
        "waste_score": {
            "score": waste_score.score_value if waste_score else 0,
            "level": waste_score.level if waste_score else "LOW",
            "summary": waste_score.summary_text if waste_score else "No scan active.",
            "signals": [
                {
                    "title": s.title,
                    "detail": s.detail,
                    "severity": s.severity,
                    "impact_bytes": s.impact_bytes,
                }
                for s in (waste_score.signals if waste_score else [])
            ],
        },
        "large_files": {
            "threshold_mb": state.large_threshold_mb,
            "count": state.large_report.count if state.large_report else 0,
            "total_size_label": state.large_report.total_size_label if state.large_report else "0 B",
            "files": [
                {
                    "name": f.name,
                    "path": f.path,
                    "category": f.category,
                    "size_bytes": f.size_bytes,
                    "size_label": f.size_label,
                    "modified_at": f.modified_at,
                }
                for f in (state.large_report.files if state.large_report else [])
            ],
        },
        "stale_files": {
            "days_threshold": state.stale_days_threshold,
            "count": state.stale_report.count if state.stale_report else 0,
            "total_size_label": state.stale_report.total_size_label if state.stale_report else "0 B",
            "files": [
                {
                    "name": f.name,
                    "path": f.path,
                    "category": f.category,
                    "size_bytes": f.size_bytes,
                    "size_label": f.size_label,
                    "modified_at": f.modified_at,
                    "age_days": f.age_days,
                }
                for f in (state.stale_report.files if state.stale_report else [])
            ],
        },
        "temp_files": {
            "count": state.temp_report.count if state.temp_report else 0,
            "total_size_label": state.temp_report.total_size_label if state.temp_report else "0 B",
            "files": [
                {
                    "name": f.name,
                    "path": f.path,
                    "category": f.category,
                    "size_bytes": f.size_bytes,
                    "size_label": f.size_label,
                    "modified_at": f.modified_at,
                    "reason": f.reason,
                }
                for f in (state.temp_report.files if state.temp_report else [])
            ],
        },
        "recovery_simulator": {
            "tiers": sim_tiers,
            "disclaimer": recovery.disclaimer if recovery else "",
        },
    }


@app.get("/api/duplicates")
def get_duplicates() -> dict[str, Any]:
    """Retrieve exact duplicate groups and redundancy metrics."""
    with state.lock:
        scan_data = _build_full_scan_data()
        dup_report = state.duplicates or DuplicateReport()

    return {
        "group_count": dup_report.group_count,
        "duplicate_files_count": dup_report.duplicate_files,
        "redundant_files_count": dup_report.redundant_files,
        "redundant_bytes": dup_report.redundant_bytes,
        "redundant_size_label": dup_report.redundant_size_label,
        "groups": scan_data["duplicateGroups"],
    }


@app.get("/api/recommendations")
def get_recommendations() -> dict[str, Any]:
    """Retrieve prioritized waste review recommendations."""
    with state.lock:
        scan_data = _build_full_scan_data()
        rec_report = state.recommendations

    return {
        "total_count": rec_report.total_count if rec_report else 0,
        "high_priority_count": rec_report.high_count if rec_report else 0,
        "medium_priority_count": rec_report.medium_count if rec_report else 0,
        "low_priority_count": rec_report.low_count if rec_report else 0,
        "recommendations": scan_data["recommendations"],
    }


@app.post("/api/qwen/analyze")
def analyze_with_qwen(req: QwenAnalyzeRequest) -> dict[str, Any]:
    """Generate executive waste analysis using TCET CoE Qwen."""
    with state.lock:
        if not state.records:
            raise HTTPException(status_code=400, detail="No scan data available. Please scan a folder first.")

        summary = summarize(state.records)
        sanitized_ev = sanitize_evidence(
            summary=summary,
            cat_distribution=state.cat_distribution,
            duplicate_report=state.duplicates,
            large_report=state.large_report,
            stale_report=state.stale_report,
            temp_report=state.temp_report,
            rec_report=state.recommendations,
            recovery=state.recovery,
        )

    service = _get_qwen_service()
    raw_analysis = service.analyze_waste_sync(sanitized_ev, enable_thinking=req.enable_thinking)

    with state.lock:
        state.qwen_analysis = raw_analysis

    # Parse sections for React UI structure if structured, or provide raw markdown
    return {
        "raw_text": raw_analysis,
        "model_info": {
            "model": service.config.model,
            "gateway": service.config.base_url,
            "status": "Connected",
            "timestamp": time.strftime("%Y-%m-%d"),
        },
    }


@app.post("/api/qwen/explain")
def explain_recommendation(req: QwenExplainRequest) -> dict[str, Any]:
    """Generate on-demand explanation for a single recommendation."""
    with state.lock:
        if not state.recommendations:
            raise HTTPException(status_code=400, detail="No active recommendations available.")

        target_rec = next(
            (r for r in state.recommendations.recommendations if r.id == req.recommendation_id),
            None,
        )
        if not target_rec:
            raise HTTPException(status_code=404, detail=f"Recommendation '{req.recommendation_id}' not found.")

    service = _get_qwen_service()
    explanation = service.explain_recommendation_sync(target_rec, enable_thinking=req.enable_thinking)

    with state.lock:
        state.qwen_rec_explanations[req.recommendation_id] = explanation

    return {
        "recommendation_id": req.recommendation_id,
        "explanation": explanation,
    }


@app.post("/api/qwen/ask")
def ask_qwen(req: QwenAskRequest) -> dict[str, Any]:
    """Answer questions strictly grounded in the active scan context."""
    with state.lock:
        if not state.records:
            raise HTTPException(status_code=400, detail="No scan data active. Please scan a folder first.")

        summary = summarize(state.records)
        scan_ctx = build_grounded_scan_context(
            summary=summary,
            cat_distribution=state.cat_distribution,
            duplicate_report=state.duplicates,
            large_report=state.large_report,
            stale_report=state.stale_report,
            temp_report=state.temp_report,
            rec_report=state.recommendations,
            recovery=state.recovery,
        )

    service = _get_qwen_service()
    answer = service.ask_digital_landfill_sync(
        query=req.query,
        scan_context=scan_ctx,
        chat_history=req.chat_history,
        enable_thinking=req.enable_thinking,
    )

    return {
        "query": req.query,
        "answer": answer,
        "model": service.config.model,
    }


@app.post("/api/delete")
def delete_file(req: DeleteRequest) -> dict[str, Any]:
    """Controlled, secure file deletion with pre-verification checks."""
    if not req.confirmed:
        raise HTTPException(
            status_code=400,
            detail="Explicit user confirmation is required to delete a file.",
        )

    with state.lock:
        if not state.scanned_root:
            raise HTTPException(status_code=400, detail="No active scan session.")

        target_path_str = req.path.strip()
        target_path = Path(target_path_str).resolve()
        root_path = Path(state.scanned_root).resolve()

        # Security check 1: Target path must be within currently active scanned root
        try:
            target_path.relative_to(root_path)
        except ValueError:
            raise HTTPException(
                status_code=403,
                detail=f"Security violation: Cannot delete file outside active scanned root '{root_path}'.",
            )

        # Security check 2: Target path must be present in active scan records
        matching_record = next((r for r in state.records if Path(r.path).resolve() == target_path), None)
        if not matching_record:
            raise HTTPException(
                status_code=404,
                detail="File was not found in the active scan records. Please refresh the scan.",
            )

        # Security check 3: File must physically exist
        if not target_path.exists() or not target_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=f"File '{target_path.name}' does not exist on disk or has already been removed.",
            )

        # Security check 4: Verify file size has not changed since scan
        try:
            current_size = target_path.stat().st_size
            if current_size != req.expected_size:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"File size changed since scan! Expected {req.expected_size} bytes, "
                        f"found {current_size} bytes. Deletion aborted for safety."
                    ),
                )
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Cannot inspect file metadata: {exc}")

        # Perform deletion
        try:
            os.remove(target_path)
        except PermissionError:
            raise HTTPException(status_code=403, detail="Permission denied. Cannot delete file.")
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"OS error during deletion: {exc}")

        # Update in-memory state: Remove file from records and recompute
        state.records = [r for r in state.records if Path(r.path).resolve() != target_path]
        _recompute_intelligence_locked()
        updated_scan = _build_full_scan_data()

    return {
        "status": "success",
        "message": f"Successfully deleted '{target_path.name}'. Reclaimed {format_size(req.expected_size)}.",
        "deleted_path": str(target_path),
        "reclaimed_bytes": req.expected_size,
        "data": updated_scan,
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"Starting Digital Landfill FastAPI on {host}:{port} (Mode: {DEPLOYMENT_MODE})...")
    uvicorn.run(app, host=host, port=port)
