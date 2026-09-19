"""Deterministic unit tests for Phase 3: Waste Intelligence.

Tests:
1. Extension categorization (all primary categories)
2. Unknown / missing extension -> Other
3. Storage aggregation (bytes, percentages)
4. File count aggregation (counts, percentages)
5. Large file detection (configurable thresholds, descending sort)
6. Stale file detection (age in days, neutral terminology)
7. Temporary / cache heuristic detection (extensions, ~, keywords, directories)
8. Duplicate waste calculation integration
9. Waste indicator scoring & signals (LOW, MEDIUM, HIGH)
10. Storage recovery simulation (tiers & deduplication)
11. Empty scan handling
12. Resilient handling of missing timestamps / unreadable metadata
"""

from __future__ import annotations

import os
import tempfile
import time
import unittest
from pathlib import Path

from src.duplicates import DuplicateGroup, DuplicateReport, find_duplicates
from src.models import FileRecord, format_size, format_timestamp
from src.scanner import categorize, scan_folder
from src.waste import (
    calculate_waste_score,
    find_large_files,
    find_stale_files,
    find_temp_cache_files,
    get_storage_distribution,
    simulate_recovery,
    summarize_duplicate_waste,
)


def make_record(
    name: str = "test.txt",
    path: str = "/tmp/test.txt",
    parent: str = "/tmp",
    extension: str = ".txt",
    category: str = "Documents",
    size_bytes: int = 1000,
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


class TestCategoryIntelligence(unittest.TestCase):
    def test_extension_categorization(self) -> None:
        self.assertEqual(categorize(".pdf"), "Documents")
        self.assertEqual(categorize("doc"), "Documents")
        self.assertEqual(categorize(".docx"), "Documents")
        self.assertEqual(categorize(".txt"), "Documents")
        self.assertEqual(categorize(".md"), "Documents")
        self.assertEqual(categorize(".rtf"), "Documents")

        self.assertEqual(categorize(".jpg"), "Images")
        self.assertEqual(categorize(".jpeg"), "Images")
        self.assertEqual(categorize(".png"), "Images")
        self.assertEqual(categorize(".gif"), "Images")
        self.assertEqual(categorize(".webp"), "Images")
        self.assertEqual(categorize(".svg"), "Images")

        self.assertEqual(categorize(".mp4"), "Videos")
        self.assertEqual(categorize(".mkv"), "Videos")
        self.assertEqual(categorize(".avi"), "Videos")
        self.assertEqual(categorize(".mov"), "Videos")
        self.assertEqual(categorize(".webm"), "Videos")
        self.assertEqual(categorize(".wmv"), "Videos")

        self.assertEqual(categorize(".mp3"), "Audio")
        self.assertEqual(categorize(".wav"), "Audio")
        self.assertEqual(categorize(".flac"), "Audio")
        self.assertEqual(categorize(".aac"), "Audio")
        self.assertEqual(categorize(".ogg"), "Audio")
        self.assertEqual(categorize(".m4a"), "Audio")

        self.assertEqual(categorize(".zip"), "Archives")
        self.assertEqual(categorize(".rar"), "Archives")
        self.assertEqual(categorize(".7z"), "Archives")
        self.assertEqual(categorize(".tar"), "Archives")
        self.assertEqual(categorize(".gz"), "Archives")
        self.assertEqual(categorize(".bz2"), "Archives")

        self.assertEqual(categorize(".py"), "Code")
        self.assertEqual(categorize(".js"), "Code")
        self.assertEqual(categorize(".ts"), "Code")
        self.assertEqual(categorize(".java"), "Code")
        self.assertEqual(categorize(".cpp"), "Code")
        self.assertEqual(categorize(".html"), "Code")
        self.assertEqual(categorize(".css"), "Code")
        self.assertEqual(categorize(".sql"), "Code")
        self.assertEqual(categorize(".ps1"), "Code")

        self.assertEqual(categorize(".parquet"), "Datasets")
        self.assertEqual(categorize(".feather"), "Datasets")
        self.assertEqual(categorize(".h5"), "Datasets")
        self.assertEqual(categorize(".arrow"), "Datasets")
        self.assertEqual(categorize(".csv"), "Datasets")

        self.assertEqual(categorize(".ppt"), "Presentations")
        self.assertEqual(categorize(".pptx"), "Presentations")

        self.assertEqual(categorize(".xls"), "Spreadsheets")
        self.assertEqual(categorize(".xlsx"), "Spreadsheets")
        self.assertEqual(categorize(".ods"), "Spreadsheets")

    def test_unknown_extension_to_other(self) -> None:
        self.assertEqual(categorize(".unknown_ext_xyz"), "Other")
        self.assertEqual(categorize(""), "Other")
        self.assertEqual(categorize("—"), "Other")
        self.assertEqual(categorize(".dat"), "Other")

    def test_custom_extension_override(self) -> None:
        custom = {"myformat": "Datasets", "txt": "Special"}
        self.assertEqual(categorize(".myformat", custom), "Datasets")
        self.assertEqual(categorize(".txt", custom), "Special")
        self.assertEqual(categorize(".pdf", custom), "Documents")


class TestStorageDistribution(unittest.TestCase):
    def test_distribution_aggregation(self) -> None:
        records = [
            make_record(name="doc1.pdf", category="Documents", size_bytes=2000),
            make_record(name="doc2.docx", category="Documents", size_bytes=1000),
            make_record(name="video.mp4", category="Videos", size_bytes=7000),
        ]
        dist = get_storage_distribution(records)

        self.assertEqual(len(dist), 2)
        # Sorted largest storage first (Videos: 7000 B, Documents: 3000 B)
        first, second = dist
        self.assertEqual(first.category, "Videos")
        self.assertEqual(first.file_count, 1)
        self.assertEqual(first.total_bytes, 7000)
        self.assertEqual(first.storage_pct, 70.0)
        self.assertEqual(first.files_pct, 33.3)

        self.assertEqual(second.category, "Documents")
        self.assertEqual(second.file_count, 2)
        self.assertEqual(second.total_bytes, 3000)
        self.assertEqual(second.storage_pct, 30.0)
        self.assertEqual(second.files_pct, 66.7)

    def test_distribution_empty_records(self) -> None:
        self.assertEqual(get_storage_distribution([]), [])


class TestLargeFileIntelligence(unittest.TestCase):
    def test_find_large_files_default_and_custom(self) -> None:
        records = [
            make_record(name="tiny.txt", size_bytes=100),
            make_record(name="mid.bin", size_bytes=50 * 1024 * 1024),
            make_record(name="big1.zip", size_bytes=150 * 1024 * 1024),
            make_record(name="big2.iso", size_bytes=300 * 1024 * 1024),
        ]

        # Default 100 MB threshold
        report = find_large_files(records, threshold_bytes=100 * 1024 * 1024)
        self.assertEqual(report.count, 2)
        self.assertEqual(report.total_bytes, 450 * 1024 * 1024)
        self.assertEqual(report.files[0].name, "big2.iso")
        self.assertEqual(report.files[1].name, "big1.zip")

        # Custom 20 MB threshold
        report_20 = find_large_files(records, threshold_bytes=20 * 1024 * 1024)
        self.assertEqual(report_20.count, 3)

    def test_find_large_files_empty(self) -> None:
        report = find_large_files([])
        self.assertEqual(report.count, 0)
        self.assertEqual(report.total_bytes, 0)
        self.assertEqual(report.files, [])


class TestStaleFileIntelligence(unittest.TestCase):
    def test_find_stale_files(self) -> None:
        ref_time = 1_700_000_000.0  # reference time
        day_secs = 86400

        records = [
            # 10 days old
            make_record(name="recent.txt", modified_timestamp=ref_time - (10 * day_secs)),
            # 200 days old (> 180 threshold)
            make_record(name="stale1.txt", size_bytes=4000, modified_timestamp=ref_time - (200 * day_secs)),
            # 400 days old (> 180 threshold)
            make_record(name="stale2.txt", size_bytes=6000, modified_timestamp=ref_time - (400 * day_secs)),
        ]

        report = find_stale_files(records, days_threshold=180, reference_time=ref_time)
        self.assertEqual(report.count, 2)
        self.assertEqual(report.total_bytes, 10000)
        # Oldest first
        self.assertEqual(report.files[0].name, "stale2.txt")
        self.assertEqual(report.files[0].age_days, 400)
        self.assertEqual(report.files[1].name, "stale1.txt")
        self.assertEqual(report.files[1].age_days, 200)

    def test_stale_files_fallback_to_string_modified_at(self) -> None:
        # String date parsing fallback
        r = make_record(name="parsed.txt", modified_at="2020-01-01 12:00", modified_timestamp=0.0)
        report = find_stale_files([r], days_threshold=180, reference_time=time.time())
        self.assertEqual(report.count, 1)
        self.assertGreater(report.files[0].age_days, 365)


class TestTempCacheDetection(unittest.TestCase):
    def test_heuristic_detection_rules(self) -> None:
        records = [
            make_record(name="notes.txt", path="/home/user/notes.txt", extension=".txt"),
            make_record(name="data.tmp", path="/home/user/data.tmp", extension=".tmp"),
            make_record(name="~$proposal.docx", path="/home/user/~$proposal.docx", extension=".docx"),
            make_record(name="app_cache.json", path="/home/user/app_cache.json", extension=".json"),
            make_record(name="module.cpython-311.pyc", path="/home/user/__pycache__/module.pyc", extension=".pyc"),
            make_record(name="old_db.bak", path="/home/user/old_db.bak", extension=".bak"),
            make_record(name="test.py", path="/home/user/project/.pytest_cache/test.py", extension=".py"),
        ]

        report = find_temp_cache_files(records)
        detected_names = {f.name for f in report.files}

        self.assertIn("data.tmp", detected_names)
        self.assertIn("~$proposal.docx", detected_names)
        self.assertIn("app_cache.json", detected_names)
        self.assertIn("module.cpython-311.pyc", detected_names)
        self.assertIn("old_db.bak", detected_names)
        self.assertIn("test.py", detected_names)
        self.assertNotIn("notes.txt", detected_names)

        # Check reasons
        reasons_by_name = {f.name: f.reason for f in report.files}
        self.assertIn(".tmp", reasons_by_name["data.tmp"])
        self.assertIn("~", reasons_by_name["~$proposal.docx"])
        self.assertIn("cache", reasons_by_name["app_cache.json"])
        self.assertTrue(
            "cache" in reasons_by_name["module.cpython-311.pyc"].lower()
            or ".pyc" in reasons_by_name["module.cpython-311.pyc"].lower()
        )


class TestDuplicateWasteAndScore(unittest.TestCase):
    def test_duplicate_waste_summary(self) -> None:
        # 2 groups
        r1 = make_record(name="d1.txt", path="/a/d1.txt", size_bytes=1000)
        r2 = make_record(name="d2.txt", path="/b/d2.txt", size_bytes=1000)
        r3 = make_record(name="d3.txt", path="/c/d3.txt", size_bytes=1000)

        group = DuplicateGroup(sha256="abc123hash", size_bytes=1000, files=(r1, r2, r3))
        report = DuplicateReport(groups=[group], candidate_files=3, hashed_files=3, bytes_hashed=3000)

        summary = summarize_duplicate_waste(report)
        self.assertTrue(summary.has_run)
        self.assertEqual(summary.group_count, 1)
        self.assertEqual(summary.duplicate_files, 3)
        self.assertEqual(summary.redundant_files, 2)
        self.assertEqual(summary.redundant_bytes, 2000)

    def test_waste_score_calculation(self) -> None:
        records = [
            make_record(name="f1.txt", size_bytes=1000),
            make_record(name="f2.txt", size_bytes=1000),
            make_record(name="cache.tmp", size_bytes=5000),
        ]
        score_report = calculate_waste_score(records)
        self.assertIn(score_report.level, ("LOW", "MEDIUM", "HIGH"))
        self.assertGreaterEqual(score_report.score_value, 0)
        self.assertLessEqual(score_report.score_value, 100)
        self.assertGreaterEqual(len(score_report.signals), 3)

    def test_waste_score_empty(self) -> None:
        score_report = calculate_waste_score([])
        self.assertEqual(score_report.level, "LOW")
        self.assertEqual(score_report.score_value, 0)


class TestStorageRecoverySimulator(unittest.TestCase):
    def test_tiered_recovery_simulation(self) -> None:
        now = time.time()
        r1 = make_record(name="orig.txt", path="/docs/orig.txt", size_bytes=2000, modified_timestamp=now)
        r2 = make_record(name="copy.txt", path="/docs/copy.txt", size_bytes=2000, modified_timestamp=now)
        r_temp = make_record(name="app.tmp", path="/docs/app.tmp", size_bytes=1500, modified_timestamp=now)
        r_stale = make_record(name="archive.dat", path="/docs/archive.dat", size_bytes=3000, modified_timestamp=1.0)

        records = [r1, r2, r_temp, r_stale]
        group = DuplicateGroup(sha256="hash123", size_bytes=2000, files=(r1, r2))
        dup_report = DuplicateReport(groups=[group])

        recovery = simulate_recovery(records, duplicate_report=dup_report)

        # Tier 1 = Exact duplicate redundant copy (2000 B)
        self.assertEqual(recovery.tier1_exact_bytes, 2000)
        self.assertEqual(recovery.exact_recoverable_files, 1)

        # Tier 2 = Tier 1 (2000) + Temp (1500) = 3500 B
        self.assertEqual(recovery.tier2_with_temp_bytes, 3500)

        # Tier 3 = Tier 2 (3500) + Stale (3000) = 6500 B
        self.assertEqual(recovery.tier3_full_review_bytes, 6500)

    def test_simulation_empty(self) -> None:
        recovery = simulate_recovery([])
        self.assertEqual(recovery.tier1_exact_bytes, 0)
        self.assertEqual(recovery.tier2_with_temp_bytes, 0)
        self.assertEqual(recovery.tier3_full_review_bytes, 0)


class TestEndToEndScanningWithWasteIntelligence(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()

        # Create files
        (self.root / "docs").mkdir()
        (self.root / "docs" / "report.pdf").write_bytes(b"pdf-content" * 100)
        (self.root / "docs" / "data.csv").write_bytes(b"col1,col2\n1,2\n" * 50)
        (self.root / "image.png").write_bytes(b"png-data" * 20)
        (self.root / "script.py").write_bytes(b"print('hello')" * 10)
        (self.root / "temp_file.tmp").write_bytes(b"temp-data" * 10)

        # Duplicate files
        dup_bytes = b"duplicate-bytes" * 500
        (self.root / "orig.bin").write_bytes(dup_bytes)
        (self.root / "copy.bin").write_bytes(dup_bytes)

    def test_full_pipeline_read_only(self) -> None:
        records, errors = scan_folder(self.root)
        self.assertEqual(errors, [])
        self.assertGreater(len(records), 5)

        # Storage distribution
        dist = get_storage_distribution(records)
        cats = {d.category for d in dist}
        self.assertIn("Documents", cats)
        self.assertIn("Datasets", cats)
        self.assertIn("Images", cats)
        self.assertIn("Code", cats)

        # Duplicates
        dup_report = find_duplicates(records)
        self.assertEqual(dup_report.group_count, 1)

        # Temp files
        temp_report = find_temp_cache_files(records)
        self.assertGreaterEqual(temp_report.count, 1)
        self.assertTrue(any(f.name == "temp_file.tmp" for f in temp_report.files))

        # Recovery simulation
        recovery = simulate_recovery(records, duplicate_report=dup_report, temp_report=temp_report)
        self.assertGreater(recovery.tier1_exact_bytes, 0)
        self.assertGreaterEqual(recovery.tier2_with_temp_bytes, recovery.tier1_exact_bytes)


if __name__ == "__main__":
    unittest.main()
