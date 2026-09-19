"""Phase 3 — Waste Intelligence Engine.

Provides local-first, read-only analysis of scanned file inventory to identify
storage distribution patterns, unusually large files, potentially stale files,
heuristic temporary/cache candidates, exact duplicate waste, and simulated
storage recovery potential.

All functions are strictly read-only and operate in memory on metadata.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import time
from typing import Sequence

from src.duplicates import DuplicateReport
from src.models import FileRecord, format_size


# ---------------------------------------------------------------------------
# 1. Storage Distribution & Category Intelligence
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class CategoryDistribution:
    category: str
    file_count: int
    total_bytes: int
    total_size_label: str
    storage_pct: float
    files_pct: float


def get_storage_distribution(records: Sequence[FileRecord]) -> list[CategoryDistribution]:
    """Calculate storage and file count breakdown per category."""
    if not records:
        return []

    total_files = len(records)
    total_bytes = sum(r.size_bytes for r in records)

    cat_files: dict[str, int] = defaultdict(int)
    cat_bytes: dict[str, int] = defaultdict(int)

    for r in records:
        cat_files[r.category] += 1
        cat_bytes[r.category] += r.size_bytes

    results: list[CategoryDistribution] = []
    for cat, count in cat_files.items():
        size = cat_bytes[cat]
        storage_pct = (size / total_bytes * 100.0) if total_bytes > 0 else 0.0
        files_pct = (count / total_files * 100.0) if total_files > 0 else 0.0

        results.append(
            CategoryDistribution(
                category=cat,
                file_count=count,
                total_bytes=size,
                total_size_label=format_size(size),
                storage_pct=round(storage_pct, 1),
                files_pct=round(files_pct, 1),
            )
        )

    # Sort largest storage first, then largest file count
    results.sort(key=lambda c: (-c.total_bytes, -c.file_count, c.category))
    return results


# ---------------------------------------------------------------------------
# 2. Large File Intelligence
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class LargeFileRecord:
    name: str
    path: str
    extension: str
    category: str
    size_bytes: int
    size_label: str
    modified_at: str


@dataclass(slots=True)
class LargeFilesReport:
    threshold_bytes: int
    threshold_mb: float
    count: int
    total_bytes: int
    total_size_label: str
    files: list[LargeFileRecord] = field(default_factory=list)


def find_large_files(
    records: Sequence[FileRecord],
    threshold_bytes: int = 100 * 1024 * 1024,
) -> LargeFilesReport:
    """Identify files whose size is at or above the threshold (default 100 MB)."""
    large: list[LargeFileRecord] = []
    total_bytes = 0

    for r in records:
        if r.size_bytes >= threshold_bytes:
            large.append(
                LargeFileRecord(
                    name=r.name,
                    path=r.path,
                    extension=r.extension,
                    category=r.category,
                    size_bytes=r.size_bytes,
                    size_label=r.size_label,
                    modified_at=r.modified_at,
                )
            )
            total_bytes += r.size_bytes

    large.sort(key=lambda f: (-f.size_bytes, f.path))
    threshold_mb = round(threshold_bytes / (1024 * 1024), 1)

    return LargeFilesReport(
        threshold_bytes=threshold_bytes,
        threshold_mb=threshold_mb,
        count=len(large),
        total_bytes=total_bytes,
        total_size_label=format_size(total_bytes),
        files=large,
    )


# ---------------------------------------------------------------------------
# 3. Old File Intelligence (Potentially Stale Files)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class StaleFileRecord:
    name: str
    path: str
    category: str
    size_bytes: int
    size_label: str
    modified_at: str
    age_days: int


@dataclass(slots=True)
class StaleFilesReport:
    days_threshold: int
    count: int
    total_bytes: int
    total_size_label: str
    files: list[StaleFileRecord] = field(default_factory=list)


def _get_record_mtime(record: FileRecord) -> float | None:
    """Extract modification timestamp from FileRecord with fallback to parsing string."""
    if getattr(record, "modified_timestamp", 0.0) > 0:
        return record.modified_timestamp

    if record.modified_at and record.modified_at != "—":
        try:
            dt = datetime.strptime(record.modified_at, "%Y-%m-%d %H:%M")
            return dt.timestamp()
        except (ValueError, OverflowError):
            pass
    return None


def find_stale_files(
    records: Sequence[FileRecord],
    days_threshold: int = 180,
    reference_time: float | None = None,
) -> StaleFilesReport:
    """Identify potentially stale files based on modification age (default 180 days).

    Terminology note: Labeled neutrally as 'potentially stale' or 'review candidates'.
    """
    now = time.time() if reference_time is None else reference_time
    stale: list[StaleFileRecord] = []
    total_bytes = 0

    for r in records:
        mtime = _get_record_mtime(r)
        if mtime is None or mtime <= 0:
            continue

        diff_seconds = now - mtime
        if diff_seconds <= 0:
            continue

        age_days = int(diff_seconds // 86400)
        if age_days >= days_threshold:
            stale.append(
                StaleFileRecord(
                    name=r.name,
                    path=r.path,
                    category=r.category,
                    size_bytes=r.size_bytes,
                    size_label=r.size_label,
                    modified_at=r.modified_at,
                    age_days=age_days,
                )
            )
            total_bytes += r.size_bytes

    # Sort oldest first, then largest size
    stale.sort(key=lambda f: (-f.age_days, -f.size_bytes, f.path))

    return StaleFilesReport(
        days_threshold=days_threshold,
        count=len(stale),
        total_bytes=total_bytes,
        total_size_label=format_size(total_bytes),
        files=stale,
    )


# ---------------------------------------------------------------------------
# 4. Temporary / Cache-like File Detection
# ---------------------------------------------------------------------------

TEMP_EXTENSIONS = {
    ".tmp",
    ".temp",
    ".cache",
    ".bak",
    ".old",
    ".log",
    ".swp",
    ".swo",
    ".ds_store",
    ".pyc",
    ".pyo",
    ".coverage",
    ".part",
    ".crdownload",
    ".wbk",
    ".dmp",
}

TEMP_DIR_NAMES = {
    "temp",
    "tmp",
    "cache",
    ".cache",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".sass-cache",
    ".parcel-cache",
}

TEMP_NAME_KEYWORDS = ["temp", "tmp", "cache", "backup"]


@dataclass(slots=True)
class TempFileRecord:
    name: str
    path: str
    category: str
    size_bytes: int
    size_label: str
    modified_at: str
    reason: str


@dataclass(slots=True)
class TempFilesReport:
    count: int
    total_bytes: int
    total_size_label: str
    files: list[TempFileRecord] = field(default_factory=list)


def _detect_temp_reason(record: FileRecord) -> str | None:
    """Check heuristic rules to detect if a file appears temporary or cache-like."""
    name_lower = record.name.lower()
    ext_lower = ("." + record.extension.lower().lstrip(".")) if record.extension != "—" else ""
    path_obj = Path(record.path)

    reasons: list[str] = []

    # 1. Extension check
    if ext_lower in TEMP_EXTENSIONS:
        reasons.append(f"Extension: {ext_lower}")
    elif name_lower.endswith((".tmp", ".temp", ".bak", ".old", ".log", ".swp")):
        reasons.append("Temp extension in filename")

    # 2. Temporary lock / backup patterns
    if name_lower.startswith("~$") or name_lower.startswith("~"):
        reasons.append("Temporary lock/swap file pattern ('~')")

    # 3. Keyword check in filename
    stem = path_obj.stem.lower()
    for kw in TEMP_NAME_KEYWORDS:
        if kw in stem and f"Extension: {ext_lower}" not in reasons:
            reasons.append(f"Filename contains '{kw}'")
            break

    # 4. Parent directory heuristics
    for part in path_obj.parent.parts:
        part_lower = part.lower()
        if part_lower in TEMP_DIR_NAMES:
            reasons.append(f"Located inside cache/temp directory: {part}")
            break
        if part_lower.endswith(".cache") or "node_modules/.cache" in record.path.replace("\\", "/").lower():
            reasons.append("Located inside cache directory")
            break

    if reasons:
        return "; ".join(reasons)
    return None


def find_temp_cache_files(records: Sequence[FileRecord]) -> TempFilesReport:
    """Identify files that heuristics indicate may be temporary or cache-like.

    Important: These are potential review candidates only; never marked as guaranteed waste.
    """
    temp_files: list[TempFileRecord] = []
    total_bytes = 0

    for r in records:
        reason = _detect_temp_reason(r)
        if reason:
            temp_files.append(
                TempFileRecord(
                    name=r.name,
                    path=r.path,
                    category=r.category,
                    size_bytes=r.size_bytes,
                    size_label=r.size_label,
                    modified_at=r.modified_at,
                    reason=reason,
                )
            )
            total_bytes += r.size_bytes

    temp_files.sort(key=lambda f: (-f.size_bytes, f.path))

    return TempFilesReport(
        count=len(temp_files),
        total_bytes=total_bytes,
        total_size_label=format_size(total_bytes),
        files=temp_files,
    )


# ---------------------------------------------------------------------------
# 5. Redundant Storage Analysis (Phase 2 Integration)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class DuplicateWasteSummary:
    has_run: bool
    group_count: int
    duplicate_files: int
    redundant_files: int
    redundant_bytes: int
    redundant_size_label: str
    total_duplicate_bytes: int
    total_duplicate_size_label: str


def summarize_duplicate_waste(
    duplicate_report: DuplicateReport | None,
) -> DuplicateWasteSummary:
    """Extract redundant duplicate storage figures from Phase 2 DuplicateReport."""
    if duplicate_report is None:
        return DuplicateWasteSummary(
            has_run=False,
            group_count=0,
            duplicate_files=0,
            redundant_files=0,
            redundant_bytes=0,
            redundant_size_label="0 B",
            total_duplicate_bytes=0,
            total_duplicate_size_label="0 B",
        )

    total_dup_bytes = sum(g.total_bytes for g in duplicate_report.groups)

    return DuplicateWasteSummary(
        has_run=True,
        group_count=duplicate_report.group_count,
        duplicate_files=duplicate_report.duplicate_files,
        redundant_files=duplicate_report.redundant_files,
        redundant_bytes=duplicate_report.redundant_bytes,
        redundant_size_label=duplicate_report.redundant_size_label,
        total_duplicate_bytes=total_dup_bytes,
        total_duplicate_size_label=format_size(total_dup_bytes),
    )


# ---------------------------------------------------------------------------
# 6. Waste Intelligence Score & Contributing Signals
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class WasteSignal:
    title: str
    detail: str
    severity: str  # "low", "medium", "high", "neutral"
    impact_bytes: int


@dataclass(slots=True)
class WasteScoreReport:
    level: str  # "LOW", "MEDIUM", "HIGH"
    score_value: int  # 0 to 100
    signals: list[WasteSignal]
    summary_text: str


def calculate_waste_score(
    records: Sequence[FileRecord],
    duplicate_report: DuplicateReport | None = None,
    large_report: LargeFilesReport | None = None,
    stale_report: StaleFilesReport | None = None,
    temp_report: TempFilesReport | None = None,
) -> WasteScoreReport:
    """Calculate transparent analytical waste indicator from detected signals.

    This is an analytical heuristic indicator showing potential waste density.
    It does NOT mandate deletion.
    """
    if not records:
        return WasteScoreReport(
            level="LOW",
            score_value=0,
            signals=[],
            summary_text="No scanned files to analyze.",
        )

    total_files = len(records)
    total_bytes = sum(r.size_bytes for r in records)

    # Compute sub-reports if not provided
    if large_report is None:
        large_report = find_large_files(records)
    if stale_report is None:
        stale_report = find_stale_files(records)
    if temp_report is None:
        temp_report = find_temp_cache_files(records)

    dup_summary = summarize_duplicate_waste(duplicate_report)

    signals: list[WasteSignal] = []
    score_points = 0.0

    # 1. Duplicate Waste Signal
    if dup_summary.has_run:
        if dup_summary.redundant_bytes > 0:
            dup_ratio = (dup_summary.redundant_bytes / total_bytes) if total_bytes > 0 else 0.0
            sev = "high" if dup_ratio > 0.15 else "medium" if dup_ratio > 0.05 else "low"
            signals.append(
                WasteSignal(
                    title="Exact duplicate waste",
                    detail=f"{dup_summary.redundant_size_label} recoverable across {dup_summary.redundant_files:,} redundant copies ({dup_summary.group_count:,} groups)",
                    severity=sev,
                    impact_bytes=dup_summary.redundant_bytes,
                )
            )
            score_points += min(40.0, dup_ratio * 150.0 + (10.0 if dup_summary.redundant_files > 0 else 0.0))
        else:
            signals.append(
                WasteSignal(
                    title="Exact duplicates",
                    detail="0 redundant duplicate bytes found",
                    severity="low",
                    impact_bytes=0,
                )
            )
    else:
        signals.append(
            WasteSignal(
                title="Exact duplicate scan",
                detail="Not run yet (click 'Find exact duplicates' to compute byte-level duplicate waste)",
                severity="neutral",
                impact_bytes=0,
            )
        )

    # 2. Temporary / Cache Candidates Signal
    if temp_report.count > 0:
        temp_ratio = (temp_report.total_bytes / total_bytes) if total_bytes > 0 else 0.0
        sev = "high" if temp_ratio > 0.10 or temp_report.count > 50 else "medium" if temp_ratio > 0.03 or temp_report.count > 10 else "low"
        signals.append(
            WasteSignal(
                title="Temporary / cache-like candidates",
                detail=f"{temp_report.total_size_label} in {temp_report.count:,} files matching temporary/cache patterns",
                severity=sev,
                impact_bytes=temp_report.total_bytes,
            )
        )
        score_points += min(25.0, temp_ratio * 100.0 + min(15.0, temp_report.count * 0.5))
    else:
        signals.append(
            WasteSignal(
                title="Temporary / cache-like files",
                detail="No temporary or cache patterns identified",
                severity="low",
                impact_bytes=0,
            )
        )

    # 3. Potentially Stale Files Signal
    if stale_report.count > 0:
        stale_ratio = (stale_report.total_bytes / total_bytes) if total_bytes > 0 else 0.0
        stale_file_ratio = (stale_report.count / total_files) if total_files > 0 else 0.0
        sev = "medium" if stale_ratio > 0.25 or stale_file_ratio > 0.40 else "low"
        signals.append(
            WasteSignal(
                title="Potentially stale files",
                detail=f"{stale_report.total_size_label} in {stale_report.count:,} files older than {stale_report.days_threshold} days",
                severity=sev,
                impact_bytes=stale_report.total_bytes,
            )
        )
        score_points += min(20.0, stale_ratio * 40.0 + stale_file_ratio * 20.0)

    # 4. Large Files Signal
    if large_report.count > 0:
        large_ratio = (large_report.total_bytes / total_bytes) if total_bytes > 0 else 0.0
        signals.append(
            WasteSignal(
                title="Large files",
                detail=f"{large_report.total_size_label} in {large_report.count:,} files (>= {large_report.threshold_mb} MB each)",
                severity="medium" if large_ratio > 0.30 else "low",
                impact_bytes=large_report.total_bytes,
            )
        )
        score_points += min(15.0, large_ratio * 30.0 + min(10.0, large_report.count * 1.0))

    final_score = int(round(min(100.0, max(0.0, score_points))))

    if final_score >= 50 or (dup_summary.has_run and (dup_summary.redundant_bytes / (total_bytes or 1)) >= 0.20):
        level = "HIGH"
        summary_text = "High concentration of potential waste signals (duplicates, cache, or stale files)."
    elif final_score >= 20 or (dup_summary.has_run and (dup_summary.redundant_bytes / (total_bytes or 1)) >= 0.05):
        level = "MEDIUM"
        summary_text = "Moderate waste signals detected. Opportunity for storage recovery and review."
    else:
        level = "LOW"
        summary_text = "Low waste signals detected. Inventory appears relatively clean."

    return WasteScoreReport(
        level=level,
        score_value=final_score,
        signals=signals,
        summary_text=summary_text,
    )


# ---------------------------------------------------------------------------
# 7. Storage Recovery Simulator
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class RecoveryEstimate:
    exact_recoverable_bytes: int
    exact_recoverable_label: str
    exact_recoverable_files: int
    temp_cache_candidate_bytes: int
    temp_cache_candidate_label: str
    temp_cache_candidate_files: int
    stale_candidate_bytes: int
    stale_candidate_label: str
    stale_candidate_files: int
    tier1_exact_bytes: int
    tier1_exact_label: str
    tier2_with_temp_bytes: int
    tier2_with_temp_label: str
    tier3_full_review_bytes: int
    tier3_full_review_label: str
    disclaimer: str = (
        "Informational simulation only. Exact duplicate recovery represents identical copies. "
        "Temporary/cache and stale pools are review candidates only. Digital Landfill is strictly "
        "read-only and never modifies or deletes files."
    )


def simulate_recovery(
    records: Sequence[FileRecord],
    duplicate_report: DuplicateReport | None = None,
    temp_report: TempFilesReport | None = None,
    stale_report: StaleFilesReport | None = None,
) -> RecoveryEstimate:
    """Calculate tiered potential storage recovery without double-counting files.

    Tier 1: Exact Duplicate Recovery (Guaranteed byte-for-byte identical copies)
    Tier 2: Duplicates + Temporary/Cache candidates
    Tier 3: Duplicates + Temporary/Cache + Potentially Stale review pool
    """
    if not records:
        return RecoveryEstimate(
            exact_recoverable_bytes=0,
            exact_recoverable_label="0 B",
            exact_recoverable_files=0,
            temp_cache_candidate_bytes=0,
            temp_cache_candidate_label="0 B",
            temp_cache_candidate_files=0,
            stale_candidate_bytes=0,
            stale_candidate_label="0 B",
            stale_candidate_files=0,
            tier1_exact_bytes=0,
            tier1_exact_label="0 B",
            tier2_with_temp_bytes=0,
            tier2_with_temp_label="0 B",
            tier3_full_review_bytes=0,
            tier3_full_review_label="0 B",
        )

    # 1. Exact Duplicate Copies
    exact_bytes = 0
    exact_files = 0
    duplicate_redundant_paths: set[str] = set()

    if duplicate_report and duplicate_report.groups:
        exact_bytes = duplicate_report.redundant_bytes
        exact_files = duplicate_report.redundant_files
        for group in duplicate_report.groups:
            if len(group.files) > 1:
                for f in group.files[1:]:
                    duplicate_redundant_paths.add(f.path)

    # 2. Temp / Cache candidates (exclude files already marked as redundant duplicate copies)
    if temp_report is None:
        temp_report = find_temp_cache_files(records)

    temp_bytes = 0
    temp_files = 0
    counted_temp_paths: set[str] = set()

    for tf in temp_report.files:
        if tf.path not in duplicate_redundant_paths:
            temp_bytes += tf.size_bytes
            temp_files += 1
            counted_temp_paths.add(tf.path)

    # 3. Stale candidates (exclude files already in duplicate redundant copies or temp candidates)
    if stale_report is None:
        stale_report = find_stale_files(records)

    stale_bytes = 0
    stale_files = 0

    for sf in stale_report.files:
        if sf.path not in duplicate_redundant_paths and sf.path not in counted_temp_paths:
            stale_bytes += sf.size_bytes
            stale_files += 1

    tier1_bytes = exact_bytes
    tier2_bytes = tier1_bytes + temp_bytes
    tier3_bytes = tier2_bytes + stale_bytes

    return RecoveryEstimate(
        exact_recoverable_bytes=exact_bytes,
        exact_recoverable_label=format_size(exact_bytes),
        exact_recoverable_files=exact_files,
        temp_cache_candidate_bytes=temp_bytes,
        temp_cache_candidate_label=format_size(temp_bytes),
        temp_cache_candidate_files=temp_files,
        stale_candidate_bytes=stale_bytes,
        stale_candidate_label=format_size(stale_bytes),
        stale_candidate_files=stale_files,
        tier1_exact_bytes=tier1_bytes,
        tier1_exact_label=format_size(tier1_bytes),
        tier2_with_temp_bytes=tier2_bytes,
        tier2_with_temp_label=format_size(tier2_bytes),
        tier3_full_review_bytes=tier3_bytes,
        tier3_full_review_label=format_size(tier3_bytes),
    )
