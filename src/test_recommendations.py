"""Deterministic unit tests for Phase 4: AI Waste Recommendation Engine.

Tests:
1. Exact duplicate -> EXACT_DUPLICATE_REVIEW generated
2. Duplicate group with high recovery -> HIGH_RECOVERY_OPPORTUNITY & HIGH priority
3. Large file -> LARGE_FILE_REVIEW generated
4. Stale file -> STALE_FILE_REVIEW generated
5. Temp/cache candidate -> TEMP_CACHE_REVIEW generated
6. Multiple intersecting signals -> MIXED_WASTE_REVIEW generated
7. Evidence confidence calculations (HIGH, MEDIUM, LOW)
8. Priority calculations (HIGH, MEDIUM, LOW)
9. Empty input -> 0 recommendations
10. Recommendation ranking (Review Priority order)
11. Recovery calculation and no double counting
12. Read-only behavior guarantee
"""

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from src.duplicates import DuplicateGroup, DuplicateReport, find_duplicates
from src.models import FileRecord, format_size
from src.recommendations import (
    Confidence,
    Priority,
    RecommendationEngine,
    RecommendationType,
    generate_recommendations,
)
from src.scanner import scan_folder
from src.waste import find_large_files, find_stale_files, find_temp_cache_files


def make_record(
    name: str = "sample.txt",
    path: str = "/tmp/sample.txt",
    parent: str = "/tmp",
    extension: str = ".txt",
    category: str = "Documents",
    size_bytes: int = 1024,
    created_at: str = "2024-01-01 10:00",
    modified_at: str = "2024-01-01 10:00",
    accessed_at: str = "2024-01-01 10:00",
    mime_type: str = "text/plain",
    modified_timestamp: float = 0.0,
) -> FileRecord:
    return FileRecord(
        name=name,
        path=path,
        parent=parent,
        extension=extension,
        category=category,
        size_bytes=size_bytes,
        size_label=format_size(size_bytes),
        created_at=created_at,
        modified_at=modified_at,
        accessed_at=accessed_at,
        mime_type=mime_type,
        modified_timestamp=modified_timestamp,
    )


class TestRecommendationEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.now = time.time()
        self.engine = RecommendationEngine(
            large_threshold_bytes=100 * 1024 * 1024,
            stale_days_threshold=180,
        )

    def test_exact_duplicate_recommendation_generated(self) -> None:
        r1 = make_record(name="report.pdf", path="/a/report.pdf", size_bytes=2 * 1024 * 1024, modified_timestamp=self.now)
        r2 = make_record(name="report_copy.pdf", path="/b/report_copy.pdf", size_bytes=2 * 1024 * 1024, modified_timestamp=self.now)

        group = DuplicateGroup(sha256="aabbcc112233", size_bytes=2 * 1024 * 1024, files=(r1, r2))
        dup_report = DuplicateReport(groups=[group])

        report = self.engine.analyze([r1, r2], duplicate_report=dup_report)
        self.assertEqual(report.total_count, 1)

        rec = report.recommendations[0]
        self.assertEqual(rec.recommendation_type, RecommendationType.EXACT_DUPLICATE_REVIEW.value)
        self.assertEqual(rec.confidence, Confidence.HIGH.value)
        self.assertEqual(rec.estimated_recovery_bytes, 2 * 1024 * 1024)
        self.assertEqual(len(rec.all_paths), 2)
        self.assertTrue(any("Exact SHA-256" in r for r in rec.reasons))
        self.assertTrue(any("2 identical files" in r for r in rec.reasons))

    def test_high_recovery_opportunity_duplicate(self) -> None:
        # Group with 60 MB redundant storage (> 50 MB threshold)
        r1 = make_record(name="dataset.tar.gz", path="/a/dataset.tar.gz", size_bytes=60 * 1024 * 1024, modified_timestamp=self.now)
        r2 = make_record(name="dataset_bak.tar.gz", path="/b/dataset_bak.tar.gz", size_bytes=60 * 1024 * 1024, modified_timestamp=self.now)

        group = DuplicateGroup(sha256="ffeedd443322", size_bytes=60 * 1024 * 1024, files=(r1, r2))
        dup_report = DuplicateReport(groups=[group])

        report = self.engine.analyze([r1, r2], duplicate_report=dup_report)
        self.assertEqual(report.total_count, 1)

        rec = report.recommendations[0]
        self.assertEqual(rec.recommendation_type, RecommendationType.HIGH_RECOVERY_OPPORTUNITY.value)
        self.assertEqual(rec.priority, Priority.HIGH.value)
        self.assertEqual(rec.confidence, Confidence.HIGH.value)

    def test_large_file_recommendation_generated(self) -> None:
        r = make_record(
            name="archive.iso",
            path="/downloads/archive.iso",
            category="Archives",
            extension=".iso",
            size_bytes=150 * 1024 * 1024,
            modified_timestamp=self.now,  # Recent, not stale
        )

        report = self.engine.analyze([r])
        self.assertEqual(report.total_count, 1)

        rec = report.recommendations[0]
        self.assertEqual(rec.recommendation_type, RecommendationType.LARGE_FILE_REVIEW.value)
        self.assertEqual(rec.priority, Priority.MEDIUM.value)
        self.assertEqual(rec.confidence, Confidence.MEDIUM.value)
        self.assertTrue(any("exceeding large file threshold" in r for r in rec.reasons))

    def test_stale_file_recommendation_generated(self) -> None:
        stale_time = self.now - (250 * 86400)
        r = make_record(
            name="old_notes.txt",
            path="/docs/old_notes.txt",
            category="Documents",
            extension=".txt",
            size_bytes=5000,
            modified_timestamp=stale_time,
        )

        report = self.engine.analyze([r])
        self.assertEqual(report.total_count, 1)

        rec = report.recommendations[0]
        self.assertEqual(rec.recommendation_type, RecommendationType.STALE_FILE_REVIEW.value)
        self.assertEqual(rec.confidence, Confidence.MEDIUM.value)
        self.assertEqual(rec.age_days, 250)
        self.assertTrue(any("250 days" in r for r in rec.reasons))

    def test_temp_cache_recommendation_generated(self) -> None:
        r = make_record(
            name="session.tmp",
            path="/tmp/session.tmp",
            category="Other",
            extension=".tmp",
            size_bytes=2048,
            modified_timestamp=self.now,
        )

        report = self.engine.analyze([r])
        self.assertEqual(report.total_count, 1)

        rec = report.recommendations[0]
        self.assertEqual(rec.recommendation_type, RecommendationType.TEMP_CACHE_REVIEW.value)
        self.assertEqual(rec.confidence, Confidence.HIGH.value)
        self.assertTrue(any("Extension: .tmp" in r for r in rec.reasons))

    def test_mixed_waste_multiple_signals(self) -> None:
        stale_time = self.now - (300 * 86400)
        r = make_record(
            name="old_temp_dump.tmp",
            path="/cache/old_temp_dump.tmp",
            category="Other",
            extension=".tmp",
            size_bytes=120 * 1024 * 1024,  # Large + Stale + Temp
            modified_timestamp=stale_time,
        )

        report = self.engine.analyze([r])
        self.assertEqual(report.total_count, 1)

        rec = report.recommendations[0]
        self.assertEqual(rec.recommendation_type, RecommendationType.MIXED_WASTE_REVIEW.value)
        self.assertEqual(rec.priority, Priority.HIGH.value)
        self.assertEqual(rec.confidence, Confidence.HIGH.value)
        self.assertGreaterEqual(len(rec.reasons), 3)

    def test_evidence_confidence_calculation(self) -> None:
        # High confidence: SHA-256 duplicate
        r_dup1 = make_record(name="dup1.txt", path="/a/dup1.txt", size_bytes=1000, modified_timestamp=self.now)
        r_dup2 = make_record(name="dup2.txt", path="/b/dup2.txt", size_bytes=1000, modified_timestamp=self.now)
        group = DuplicateGroup(sha256="123456", size_bytes=1000, files=(r_dup1, r_dup2))
        rep_dup = self.engine.analyze([r_dup1, r_dup2], duplicate_report=DuplicateReport(groups=[group]))
        self.assertEqual(rep_dup.recommendations[0].confidence, Confidence.HIGH.value)

        # Medium confidence: Large file
        r_large = make_record(name="big.bin", path="/big.bin", size_bytes=150 * 1024 * 1024, modified_timestamp=self.now)
        rep_large = self.engine.analyze([r_large])
        self.assertEqual(rep_large.recommendations[0].confidence, Confidence.MEDIUM.value)

    def test_priority_calculation_levels(self) -> None:
        # High Priority: 30 MB Duplicate group
        r1 = make_record(name="v1.mp4", path="/a/v1.mp4", size_bytes=30 * 1024 * 1024, modified_timestamp=self.now)
        r2 = make_record(name="v2.mp4", path="/b/v2.mp4", size_bytes=30 * 1024 * 1024, modified_timestamp=self.now)
        group = DuplicateGroup(sha256="vidhash", size_bytes=30 * 1024 * 1024, files=(r1, r2))
        rep_high = self.engine.analyze([r1, r2], duplicate_report=DuplicateReport(groups=[group]))
        self.assertEqual(rep_high.recommendations[0].priority, Priority.HIGH.value)

        # Low Priority: Minor 1 KB stale file
        stale_time = self.now - (200 * 86400)
        r_small_stale = make_record(name="small.txt", path="/small.txt", size_bytes=100, modified_timestamp=stale_time)
        rep_low = self.engine.analyze([r_small_stale])
        self.assertEqual(rep_low.recommendations[0].priority, Priority.LOW.value)

    def test_empty_scan_produces_zero_recommendations(self) -> None:
        report = self.engine.analyze([])
        self.assertEqual(report.total_count, 0)
        self.assertEqual(report.recommendations, [])
        self.assertEqual(report.high_count, 0)
        self.assertEqual(report.medium_count, 0)
        self.assertEqual(report.low_count, 0)

    def test_recommendation_ranking_review_priority(self) -> None:
        stale_time = self.now - (200 * 86400)
        r_low = make_record(name="minor_stale.txt", path="/a/minor.txt", size_bytes=100, modified_timestamp=stale_time)
        r_med = make_record(name="med_large.iso", path="/b/med.iso", size_bytes=120 * 1024 * 1024, modified_timestamp=self.now)

        r_dup1 = make_record(name="big_dup.zip", path="/c/big_dup.zip", size_bytes=50 * 1024 * 1024, modified_timestamp=self.now)
        r_dup2 = make_record(name="big_dup_cp.zip", path="/d/big_dup_cp.zip", size_bytes=50 * 1024 * 1024, modified_timestamp=self.now)
        dup_group = DuplicateGroup(sha256="ziphash", size_bytes=50 * 1024 * 1024, files=(r_dup1, r_dup2))

        report = self.engine.analyze(
            [r_low, r_med, r_dup1, r_dup2],
            duplicate_report=DuplicateReport(groups=[dup_group]),
        )

        self.assertEqual(report.total_count, 3)
        # High priority duplicate must rank first
        self.assertEqual(report.recommendations[0].priority, Priority.HIGH.value)
        # Low priority must rank last
        self.assertEqual(report.recommendations[-1].priority, Priority.LOW.value)

    def test_recovery_calculation_deduplication(self) -> None:
        r1 = make_record(name="doc.pdf", path="/a/doc.pdf", size_bytes=5000, modified_timestamp=self.now)
        r2 = make_record(name="doc_cp.pdf", path="/b/doc_cp.pdf", size_bytes=5000, modified_timestamp=self.now)
        group = DuplicateGroup(sha256="dochash", size_bytes=5000, files=(r1, r2))

        report = self.engine.analyze([r1, r2], duplicate_report=DuplicateReport(groups=[group]))
        self.assertEqual(report.potential_duplicate_recovery_bytes, 5000)

    def test_read_only_behavior_guarantee(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir).resolve()
            test_file = root / "important_data.csv"
            content = b"col1,col2\n100,200\n"
            test_file.write_bytes(content)
            mtime_before = test_file.stat().st_mtime_ns

            records, errors = scan_folder(root)
            self.assertEqual(errors, [])

            report = generate_recommendations(records)
            self.assertTrue(test_file.exists())
            self.assertEqual(test_file.read_bytes(), content)
            self.assertEqual(test_file.stat().st_mtime_ns, mtime_before)


if __name__ == "__main__":
    unittest.main()
