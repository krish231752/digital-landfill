"""Phase 4 — AI-Powered Waste Recommendation Engine.

Transforms analytical signals from Phase 1 (File Metadata), Phase 2 (Exact Duplicates),
and Phase 3 (Waste Intelligence) into structured, explainable, evidence-based
recommendations.

The recommendation engine is strictly local-first, privacy-preserving, and read-only.
It does NOT communicate with external APIs, does NOT upload file data, and NEVER
performs automated file deletion, renaming, or movement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Sequence

from src.duplicates import DuplicateGroup, DuplicateReport
from src.models import FileRecord, format_size
from src.waste import (
    LargeFilesReport,
    StaleFilesReport,
    TempFilesReport,
    find_large_files,
    find_stale_files,
    find_temp_cache_files,
)


class RecommendationType(str, Enum):
    EXACT_DUPLICATE_REVIEW = "EXACT_DUPLICATE_REVIEW"
    HIGH_RECOVERY_OPPORTUNITY = "HIGH_RECOVERY_OPPORTUNITY"
    LARGE_FILE_REVIEW = "LARGE_FILE_REVIEW"
    STALE_FILE_REVIEW = "STALE_FILE_REVIEW"
    TEMP_CACHE_REVIEW = "TEMP_CACHE_REVIEW"
    MIXED_WASTE_REVIEW = "MIXED_WASTE_REVIEW"


class Priority(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(slots=True)
class Recommendation:
    """A structured, explainable waste review recommendation."""

    id: str
    priority: str  # "HIGH", "MEDIUM", "LOW"
    recommendation_type: str  # RecommendationType value
    type_label: str  # Human readable label
    title: str
    target_name: str
    target_path: str
    all_paths: list[str]
    category: str
    size_bytes: int
    size_label: str
    estimated_recovery_bytes: int
    estimated_recovery_label: str
    confidence: str  # "HIGH", "MEDIUM", "LOW"
    reasons: list[str]  # "WHY THIS WAS FLAGGED"
    impact_description: str  # "POTENTIAL IMPACT"
    suggested_action: str  # "SUGGESTED ACTION"
    signals: list[str]  # Raw signal tags
    modified_at: str
    age_days: int | None
    score_weight: float  # Composite score for Review Priority ranking


@dataclass(slots=True)
class RecommendationReport:
    """Summary of recommendations produced by the engine."""

    recommendations: list[Recommendation] = field(default_factory=list)
    total_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    potential_duplicate_recovery_bytes: int = 0
    potential_duplicate_recovery_label: str = "0 B"
    total_review_pool_bytes: int = 0
    total_review_pool_label: str = "0 B"


TYPE_LABELS = {
    RecommendationType.EXACT_DUPLICATE_REVIEW.value: "Exact Duplicate Review",
    RecommendationType.HIGH_RECOVERY_OPPORTUNITY.value: "High Recovery Opportunity",
    RecommendationType.LARGE_FILE_REVIEW.value: "Large File Review",
    RecommendationType.STALE_FILE_REVIEW.value: "Potentially Stale File Review",
    RecommendationType.TEMP_CACHE_REVIEW.value: "Temporary / Cache Candidate",
    RecommendationType.MIXED_WASTE_REVIEW.value: "Mixed Waste Signals Review",
}


class RecommendationEngine:
    """Explainable local recommendation engine.

    Designed with a clean interface so that future ML classifiers or local LLM
    explanation generators (Phase 5) can be introduced without altering UI consumers.
    """

    def __init__(
        self,
        large_threshold_bytes: int = 100 * 1024 * 1024,
        stale_days_threshold: int = 180,
    ) -> None:
        self.large_threshold_bytes = large_threshold_bytes
        self.stale_days_threshold = stale_days_threshold

    def analyze(
        self,
        records: Sequence[FileRecord],
        duplicate_report: DuplicateReport | None = None,
        large_report: LargeFilesReport | None = None,
        stale_report: StaleFilesReport | None = None,
        temp_report: TempFilesReport | None = None,
    ) -> RecommendationReport:
        """Generate explainable, evidence-based recommendations from scanned signals."""
        if not records:
            return RecommendationReport()

        if large_report is None:
            large_report = find_large_files(records, threshold_bytes=self.large_threshold_bytes)
        if stale_report is None:
            stale_report = find_stale_files(records, days_threshold=self.stale_days_threshold)
        if temp_report is None:
            temp_report = find_temp_cache_files(records)

        recommendations: list[Recommendation] = []
        rec_counter = 0

        # Quick lookup dictionaries
        stale_map = {sf.path: sf for sf in stale_report.files}
        temp_map = {tf.path: tf for tf in temp_report.files}
        large_map = {lf.path: lf for lf in large_report.files}

        # Track files covered by duplicate groups
        files_in_duplicate_groups: set[str] = set()
        total_dup_recovery = 0
        total_review_bytes = 0

        # -------------------------------------------------------------------
        # 1. Evaluate Duplicate Groups
        # -------------------------------------------------------------------
        if duplicate_report and duplicate_report.groups:
            for group in duplicate_report.groups:
                if len(group.files) <= 1:
                    continue

                for f in group.files:
                    files_in_duplicate_groups.add(f.path)

                rec_counter += 1
                rec_id = f"REC-DUP-{rec_counter:03d}"
                first_file = group.files[0]
                all_paths = [f.path for f in group.files]
                redundant_bytes = group.redundant_bytes
                total_dup_recovery += redundant_bytes
                total_review_bytes += redundant_bytes

                # High Recovery Opportunity vs Exact Duplicate Review
                is_high_opp = redundant_bytes >= 50 * 1024 * 1024 or group.file_count >= 4
                rec_type = (
                    RecommendationType.HIGH_RECOVERY_OPPORTUNITY.value
                    if is_high_opp
                    else RecommendationType.EXACT_DUPLICATE_REVIEW.value
                )

                # Priority logic
                if redundant_bytes >= 10 * 1024 * 1024 or group.file_count >= 3 or group.size_bytes >= 50 * 1024 * 1024:
                    priority = Priority.HIGH.value
                    pri_weight = 3000.0
                elif redundant_bytes >= 1024 * 1024 or group.file_count >= 2:
                    priority = Priority.MEDIUM.value
                    pri_weight = 2000.0
                else:
                    priority = Priority.LOW.value
                    pri_weight = 1000.0

                # Confidence logic: exact SHA-256 match is verified mathematical certainty
                confidence = Confidence.HIGH.value
                conf_weight = 300.0

                reasons = [
                    f"Exact SHA-256 byte match across all {group.file_count} copies (hash: {group.sha256[:10]}...)",
                    f"{group.file_count} identical files stored across separate folders",
                    f"{group.redundant_size_label} redundant storage held by {group.redundant_files} non-original copies",
                ]

                # Check if group also has stale or large attributes
                if first_file.path in stale_map:
                    reasons.append(f"Copies have not been modified for {stale_map[first_file.path].age_days} days")
                if first_file.path in large_map:
                    reasons.append(f"Individual file size is large ({first_file.size_label})")

                impact_desc = (
                    f"Recoverable: {group.redundant_size_label} without data loss by retaining 1 primary copy "
                    f"and reviewing the remaining {group.redundant_files} identical copies."
                )

                suggested_action = (
                    f"Manually review the {group.file_count} duplicate locations. Keep the primary original "
                    f"in your preferred folder and review redundant copies."
                )

                signals = [
                    "sha256_exact_match",
                    f"copies:{group.file_count}",
                    f"redundant_copies:{group.redundant_files}",
                    f"redundant_bytes:{redundant_bytes}",
                ]

                # Composite score for review ranking
                mb_rec = redundant_bytes / (1024 * 1024)
                score_weight = pri_weight + min(1000.0, mb_rec * 5.0) + conf_weight

                recommendations.append(
                    Recommendation(
                        id=rec_id,
                        priority=priority,
                        recommendation_type=rec_type,
                        type_label=TYPE_LABELS[rec_type],
                        title=f"{group.file_count} Exact Copies of '{first_file.name}'",
                        target_name=first_file.name,
                        target_path=first_file.path,
                        all_paths=all_paths,
                        category=first_file.category,
                        size_bytes=group.total_bytes,
                        size_label=group.total_size_label,
                        estimated_recovery_bytes=redundant_bytes,
                        estimated_recovery_label=group.redundant_size_label,
                        confidence=confidence,
                        reasons=reasons,
                        impact_description=impact_desc,
                        suggested_action=suggested_action,
                        signals=signals,
                        modified_at=first_file.modified_at,
                        age_days=stale_map[first_file.path].age_days if first_file.path in stale_map else None,
                        score_weight=score_weight,
                    )
                )

        # -------------------------------------------------------------------
        # 2. Evaluate Standalone File Signals (Large, Stale, Temp, Mixed)
        # -------------------------------------------------------------------
        for r in records:
            # Avoid duplicate recommendations for files already grouped in duplicate analysis
            if r.path in files_in_duplicate_groups:
                continue

            is_large = r.path in large_map
            is_stale = r.path in stale_map
            is_temp = r.path in temp_map

            signal_count = sum([is_large, is_stale, is_temp])
            if signal_count == 0:
                continue

            rec_counter += 1
            rec_id = f"REC-FIL-{rec_counter:03d}"
            all_paths = [r.path]
            signals: list[str] = []
            reasons: list[str] = []

            # ---------------------------------------------------------------
            # 2A. Mixed Waste Review (Multiple Intersecting Signals)
            # ---------------------------------------------------------------
            if signal_count >= 2:
                rec_type = RecommendationType.MIXED_WASTE_REVIEW.value
                total_review_bytes += r.size_bytes

                if is_temp:
                    temp_rec = temp_map[r.path]
                    reasons.append(f"Temporary/cache heuristic: {temp_rec.reason}")
                    signals.append("temp_cache_pattern")
                if is_stale:
                    stale_rec = stale_map[r.path]
                    reasons.append(f"Unmodified for {stale_rec.age_days} days (dormant file)")
                    signals.append(f"stale_days:{stale_rec.age_days}")
                if is_large:
                    reasons.append(f"Significant file size ({r.size_label})")
                    signals.append(f"large_file:{r.size_label}")

                # Priority for mixed waste
                if (is_large and is_stale and is_temp) or (is_large and r.size_bytes >= 50 * 1024 * 1024):
                    priority = Priority.HIGH.value
                    pri_weight = 3000.0
                elif r.size_bytes >= 5 * 1024 * 1024 or (is_stale and stale_map[r.path].age_days >= 365):
                    priority = Priority.MEDIUM.value
                    pri_weight = 2000.0
                else:
                    priority = Priority.LOW.value
                    pri_weight = 1000.0

                confidence = Confidence.HIGH.value if (is_temp and is_stale) else Confidence.MEDIUM.value
                conf_weight = 300.0 if confidence == Confidence.HIGH.value else 200.0

                impact_desc = (
                    f"Potential Review Candidate: {r.size_label} held by a file matching multiple "
                    f"waste indicators ({signal_count} signals)."
                )
                suggested_action = (
                    "Inspect the file to determine if this outdated/temporary file is still necessary "
                    "or can be safely archived/cleaned."
                )

                mb_size = r.size_bytes / (1024 * 1024)
                score_weight = pri_weight + min(500.0, mb_size * 2.0) + conf_weight + (signal_count * 50.0)

                recommendations.append(
                    Recommendation(
                        id=rec_id,
                        priority=priority,
                        recommendation_type=rec_type,
                        type_label=TYPE_LABELS[rec_type],
                        title=f"Multi-Signal Candidate: '{r.name}' ({signal_count} signals)",
                        target_name=r.name,
                        target_path=r.path,
                        all_paths=all_paths,
                        category=r.category,
                        size_bytes=r.size_bytes,
                        size_label=r.size_label,
                        estimated_recovery_bytes=r.size_bytes,
                        estimated_recovery_label=r.size_label,
                        confidence=confidence,
                        reasons=reasons,
                        impact_description=impact_desc,
                        suggested_action=suggested_action,
                        signals=signals,
                        modified_at=r.modified_at,
                        age_days=stale_map[r.path].age_days if is_stale else None,
                        score_weight=score_weight,
                    )
                )

            # ---------------------------------------------------------------
            # 2B. Single Signal: Temporary / Cache Candidate
            # ---------------------------------------------------------------
            elif is_temp:
                rec_type = RecommendationType.TEMP_CACHE_REVIEW.value
                temp_rec = temp_map[r.path]
                total_review_bytes += r.size_bytes

                reasons.append(f"Heuristic pattern detected: {temp_rec.reason}")
                reasons.append(f"File size: {r.size_label} ({r.category})")
                signals.append(f"temp_reason:{temp_rec.reason}")

                if r.size_bytes >= 20 * 1024 * 1024:
                    priority = Priority.HIGH.value
                    pri_weight = 2800.0
                elif r.size_bytes >= 2 * 1024 * 1024:
                    priority = Priority.MEDIUM.value
                    pri_weight = 1800.0
                else:
                    priority = Priority.LOW.value
                    pri_weight = 900.0

                # High confidence for definite extensions (.tmp, .pyc, .bak, lock files)
                if any(k in temp_rec.reason.lower() for k in [".tmp", ".pyc", ".bak", "~", "lock", "__pycache__"]):
                    confidence = Confidence.HIGH.value
                    conf_weight = 300.0
                elif "cache" in temp_rec.reason.lower():
                    confidence = Confidence.MEDIUM.value
                    conf_weight = 200.0
                else:
                    confidence = Confidence.LOW.value
                    conf_weight = 100.0

                impact_desc = (
                    f"Temporary review pool: {r.size_label} consumed by a candidate temporary or cache file."
                )
                suggested_action = (
                    "Verify file origin. Build caches and temporary lock files can generally be refreshed "
                    "automatically if needed by applications."
                )

                mb_size = r.size_bytes / (1024 * 1024)
                score_weight = pri_weight + min(300.0, mb_size * 2.0) + conf_weight

                recommendations.append(
                    Recommendation(
                        id=rec_id,
                        priority=priority,
                        recommendation_type=rec_type,
                        type_label=TYPE_LABELS[rec_type],
                        title=f"Temporary/Cache File: '{r.name}'",
                        target_name=r.name,
                        target_path=r.path,
                        all_paths=all_paths,
                        category=r.category,
                        size_bytes=r.size_bytes,
                        size_label=r.size_label,
                        estimated_recovery_bytes=r.size_bytes,
                        estimated_recovery_label=r.size_label,
                        confidence=confidence,
                        reasons=reasons,
                        impact_description=impact_desc,
                        suggested_action=suggested_action,
                        signals=signals,
                        modified_at=r.modified_at,
                        age_days=None,
                        score_weight=score_weight,
                    )
                )

            # ---------------------------------------------------------------
            # 2C. Single Signal: Large File Review
            # ---------------------------------------------------------------
            elif is_large:
                rec_type = RecommendationType.LARGE_FILE_REVIEW.value
                total_review_bytes += r.size_bytes

                reasons.append(f"Size is {r.size_label}, exceeding large file threshold")
                reasons.append(f"Category: {r.category} ({r.extension})")
                signals.append(f"large_file:{r.size_label}")

                if r.size_bytes >= 500 * 1024 * 1024:
                    priority = Priority.HIGH.value
                    pri_weight = 2700.0
                elif r.size_bytes >= 100 * 1024 * 1024:
                    priority = Priority.MEDIUM.value
                    pri_weight = 1700.0
                else:
                    priority = Priority.LOW.value
                    pri_weight = 800.0

                confidence = Confidence.MEDIUM.value
                conf_weight = 200.0

                impact_desc = (
                    f"Storage heavy: {r.size_label} occupied on local storage by a single file."
                )
                suggested_action = (
                    "Review whether this large asset is actively used locally or suitable for external archival."
                )

                mb_size = r.size_bytes / (1024 * 1024)
                score_weight = pri_weight + min(400.0, mb_size * 1.5) + conf_weight

                recommendations.append(
                    Recommendation(
                        id=rec_id,
                        priority=priority,
                        recommendation_type=rec_type,
                        type_label=TYPE_LABELS[rec_type],
                        title=f"Large File Review: '{r.name}' ({r.size_label})",
                        target_name=r.name,
                        target_path=r.path,
                        all_paths=all_paths,
                        category=r.category,
                        size_bytes=r.size_bytes,
                        size_label=r.size_label,
                        estimated_recovery_bytes=r.size_bytes,
                        estimated_recovery_label=r.size_label,
                        confidence=confidence,
                        reasons=reasons,
                        impact_description=impact_desc,
                        suggested_action=suggested_action,
                        signals=signals,
                        modified_at=r.modified_at,
                        age_days=None,
                        score_weight=score_weight,
                    )
                )

            # ---------------------------------------------------------------
            # 2D. Single Signal: Stale File Review
            # ---------------------------------------------------------------
            elif is_stale:
                stale_rec = stale_map[r.path]
                rec_type = RecommendationType.STALE_FILE_REVIEW.value
                total_review_bytes += r.size_bytes

                reasons.append(f"Unmodified for {stale_rec.age_days} days (Last modified: {r.modified_at})")
                reasons.append(f"File size: {r.size_label} ({r.category})")
                signals.append(f"stale_age:{stale_rec.age_days}d")

                if r.size_bytes >= 50 * 1024 * 1024 and stale_rec.age_days >= 365:
                    priority = Priority.HIGH.value
                    pri_weight = 2500.0
                elif r.size_bytes >= 5 * 1024 * 1024 or stale_rec.age_days >= 365:
                    priority = Priority.MEDIUM.value
                    pri_weight = 1600.0
                else:
                    priority = Priority.LOW.value
                    pri_weight = 700.0

                confidence = Confidence.MEDIUM.value
                conf_weight = 200.0

                impact_desc = (
                    f"Dormant storage: {r.size_label} held by a file untouched for > {stale_rec.age_days} days."
                )
                suggested_action = (
                    "Inspect to confirm if this older file is still actively needed or serves historical reference."
                )

                mb_size = r.size_bytes / (1024 * 1024)
                score_weight = pri_weight + min(200.0, mb_size * 1.0) + conf_weight

                recommendations.append(
                    Recommendation(
                        id=rec_id,
                        priority=priority,
                        recommendation_type=rec_type,
                        type_label=TYPE_LABELS[rec_type],
                        title=f"Potentially Stale: '{r.name}' ({stale_rec.age_days} days old)",
                        target_name=r.name,
                        target_path=r.path,
                        all_paths=all_paths,
                        category=r.category,
                        size_bytes=r.size_bytes,
                        size_label=r.size_label,
                        estimated_recovery_bytes=r.size_bytes,
                        estimated_recovery_label=r.size_label,
                        confidence=confidence,
                        reasons=reasons,
                        impact_description=impact_desc,
                        suggested_action=suggested_action,
                        signals=signals,
                        modified_at=r.modified_at,
                        age_days=stale_rec.age_days,
                        score_weight=score_weight,
                    )
                )

        # -------------------------------------------------------------------
        # 3. Rank Recommendations by Review Priority
        # -------------------------------------------------------------------
        # Highest composite score weight first (Priority > Recovery > Confidence > Size)
        recommendations.sort(key=lambda rec: (-rec.score_weight, -rec.estimated_recovery_bytes, rec.target_name))

        high_count = sum(1 for r in recommendations if r.priority == Priority.HIGH.value)
        med_count = sum(1 for r in recommendations if r.priority == Priority.MEDIUM.value)
        low_count = sum(1 for r in recommendations if r.priority == Priority.LOW.value)

        return RecommendationReport(
            recommendations=recommendations,
            total_count=len(recommendations),
            high_count=high_count,
            medium_count=med_count,
            low_count=low_count,
            potential_duplicate_recovery_bytes=total_dup_recovery,
            potential_duplicate_recovery_label=format_size(total_dup_recovery),
            total_review_pool_bytes=total_review_bytes,
            total_review_pool_label=format_size(total_review_bytes),
        )


def generate_recommendations(
    records: Sequence[FileRecord],
    duplicate_report: DuplicateReport | None = None,
    large_report: LargeFilesReport | None = None,
    stale_report: StaleFilesReport | None = None,
    temp_report: TempFilesReport | None = None,
    large_threshold_bytes: int = 100 * 1024 * 1024,
    stale_days_threshold: int = 180,
) -> RecommendationReport:
    """Convenience helper to run the RecommendationEngine."""
    engine = RecommendationEngine(
        large_threshold_bytes=large_threshold_bytes,
        stale_days_threshold=stale_days_threshold,
    )
    return engine.analyze(
        records=records,
        duplicate_report=duplicate_report,
        large_report=large_report,
        stale_report=stale_report,
        temp_report=temp_report,
    )
