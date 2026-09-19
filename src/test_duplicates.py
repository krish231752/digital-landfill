"""Deterministic tests for exact duplicate detection.

Fixture layout (sizes in bytes):

    a1.txt, docs/a2.txt, backup/old/a3.txt   content A, 6000  -> group 1
    img.bin, copy/img_copy.bin               content B, 2048  -> group 2
    same_size_diff.txt                       content C, 6000  (same size as A, different bytes)
    unique.txt                               content D,  100  (unique size)
    empty1.txt, empty2.txt                   0 bytes          (excluded by default)

Expected: 2 groups, 5 duplicate files, 3 redundant copies,
2 * 6000 + 1 * 2048 = 14048 redundant bytes.
"""

from __future__ import annotations

import dataclasses
import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from src import duplicates
from src.duplicates import CHUNK_SIZE, find_duplicates, hash_file
from src.scanner import scan_folder

A = b"alpha-block\n" * 500  # 6000 bytes
B = bytes(range(256)) * 8  # 2048 bytes
C = b"gamma-block\n" * 500  # 6000 bytes, same size as A, different content
D = b"d" * 100

EXPECTED_REDUNDANT_BYTES = 2 * len(A) + 1 * len(B)  # 12000 + 2048 = 14048


class DuplicateDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()

        self.write("a1.txt", A)
        self.write("docs/a2.txt", A)
        self.write("backup/old/a3.txt", A)
        self.write("img.bin", B)
        self.write("copy/img_copy.bin", B)
        self.write("same_size_diff.txt", C)
        self.write("unique.txt", D)
        self.write("empty1.txt", b"")
        self.write("empty2.txt", b"")

    def write(self, rel: str, data: bytes) -> Path:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def scan(self):
        records, errors = scan_folder(self.root)
        self.assertEqual(errors, [])
        return records

    def names(self, group) -> list[str]:
        return [f.name for f in group.files]

    # ------------------------------------------------------------------ core

    def test_groups_and_redundant_storage(self) -> None:
        report = find_duplicates(self.scan())

        self.assertEqual(report.errors, [])
        self.assertEqual(report.group_count, 2)
        self.assertEqual(report.duplicate_files, 5)
        self.assertEqual(report.redundant_files, 3)
        self.assertEqual(report.redundant_bytes, EXPECTED_REDUNDANT_BYTES)
        self.assertEqual(report.redundant_bytes, 14048)

        # Largest redundant storage first.
        first, second = report.groups
        self.assertEqual(sorted(self.names(first)), ["a1.txt", "a2.txt", "a3.txt"])
        self.assertEqual(first.sha256, hashlib.sha256(A).hexdigest())
        self.assertEqual(first.file_count, 3)
        self.assertEqual(first.total_bytes, 18000)
        self.assertEqual(first.redundant_bytes, 12000)

        self.assertEqual(sorted(self.names(second)), ["img.bin", "img_copy.bin"])
        self.assertEqual(second.sha256, hashlib.sha256(B).hexdigest())
        self.assertEqual(second.file_count, 2)
        self.assertEqual(second.total_bytes, 4096)
        self.assertEqual(second.redundant_bytes, 2048)

    def test_redundant_storage_matches_independent_calculation(self) -> None:
        """Cross-check against a brute-force pass that ignores the module."""
        by_digest: dict[str, list[int]] = {}
        for path in self.root.rglob("*"):
            if path.is_file() and path.stat().st_size > 0:
                data = path.read_bytes()
                by_digest.setdefault(hashlib.sha256(data).hexdigest(), []).append(len(data))
        expected = sum(sizes[0] * (len(sizes) - 1) for sizes in by_digest.values())

        self.assertEqual(find_duplicates(self.scan()).redundant_bytes, expected)
        self.assertEqual(expected, EXPECTED_REDUNDANT_BYTES)

    def test_size_prefilter_reads_only_candidates(self) -> None:
        report = find_duplicates(self.scan())
        # 6000-byte files (a1, a2, a3, same_size_diff) + 2048-byte files (img, img_copy).
        self.assertEqual(report.candidate_files, 6)
        self.assertEqual(report.hashed_files, 6)
        self.assertEqual(report.bytes_hashed, 4 * len(A) + 2 * len(B))

    def test_same_size_different_content_is_not_grouped(self) -> None:
        report = find_duplicates(self.scan())
        grouped = {f.name for g in report.groups for f in g.files}
        self.assertNotIn("same_size_diff.txt", grouped)
        self.assertNotIn("unique.txt", grouped)

    def test_empty_files_excluded_by_default_and_includable(self) -> None:
        records = self.scan()
        default = find_duplicates(records)
        self.assertNotIn("empty1.txt", {f.name for g in default.groups for f in g.files})

        with_empty = find_duplicates(records, min_size_bytes=0)
        self.assertEqual(with_empty.group_count, 3)
        empty_group = next(g for g in with_empty.groups if g.size_bytes == 0)
        self.assertEqual(empty_group.file_count, 2)
        self.assertEqual(empty_group.redundant_bytes, 0)
        self.assertEqual(with_empty.redundant_bytes, EXPECTED_REDUNDANT_BYTES)

    def test_progress_callback(self) -> None:
        calls: list[tuple[int, int]] = []
        find_duplicates(self.scan(), progress=lambda done, total: calls.append((done, total)))
        self.assertEqual(calls[0], (1, 6))
        self.assertEqual(calls[-1], (6, 6))
        self.assertEqual(len(calls), 6)

    def test_no_records(self) -> None:
        report = find_duplicates([])
        self.assertEqual((report.group_count, report.duplicate_files, report.redundant_bytes), (0, 0, 0))

    # --------------------------------------------------------------- hashing

    def test_chunked_hash_matches_hashlib(self) -> None:
        path = self.root / "a1.txt"
        expected = hashlib.sha256(A).hexdigest()
        for chunk_size in (1, 7, 4096, CHUNK_SIZE):  # includes sizes that do not divide 6000
            with self.subTest(chunk_size=chunk_size):
                self.assertEqual(hash_file(path, chunk_size), (expected, len(A)))

    def test_hash_file_empty_file(self) -> None:
        self.assertEqual(
            hash_file(self.root / "empty1.txt"), (hashlib.sha256(b"").hexdigest(), 0)
        )

    def test_invalid_chunk_size_rejected(self) -> None:
        with self.assertRaises(ValueError):
            hash_file(self.root / "a1.txt", 0)

    # ----------------------------------------------------------- error paths

    def test_file_disappears_between_scan_and_hash(self) -> None:
        records = self.scan()
        (self.root / "docs" / "a2.txt").unlink()

        report = find_duplicates(records)

        self.assertEqual(len(report.errors), 1)
        self.assertIn("a2.txt", report.errors[0])
        self.assertIn("disappeared", report.errors[0])
        # Group A shrinks to a1 + a3; group B is unaffected.
        self.assertEqual(report.group_count, 2)
        self.assertEqual(report.duplicate_files, 4)
        self.assertEqual(report.redundant_bytes, len(A) + len(B))
        self.assertEqual(report.hashed_files, 5)

    def test_permission_error_is_reported_and_scan_continues(self) -> None:
        records = self.scan()
        real = duplicates.hash_file

        def flaky(path, chunk_size=CHUNK_SIZE):
            if Path(path).name == "a2.txt":
                raise PermissionError(13, "Permission denied", str(path))
            return real(path, chunk_size)

        with mock.patch.object(duplicates, "hash_file", flaky):
            report = find_duplicates(records)

        self.assertEqual(len(report.errors), 1)
        self.assertIn("a2.txt", report.errors[0])
        self.assertIn("permission denied", report.errors[0])
        self.assertEqual(report.duplicate_files, 4)
        self.assertEqual(report.redundant_bytes, len(A) + len(B))

    def test_other_os_errors_are_reported(self) -> None:
        records = self.scan()
        real = duplicates.hash_file

        def broken(path, chunk_size=CHUNK_SIZE):
            if Path(path).name == "img.bin":
                raise OSError(5, "Input/output error", str(path))
            return real(path, chunk_size)

        with mock.patch.object(duplicates, "hash_file", broken):
            report = find_duplicates(records)

        self.assertEqual(len(report.errors), 1)
        self.assertIn("Input/output error", report.errors[0])
        # img_copy.bin is left alone in its group, so only group A remains.
        self.assertEqual(report.group_count, 1)

    def test_file_changed_since_scan_is_excluded(self) -> None:
        records = self.scan()
        with open(self.root / "docs" / "a2.txt", "ab") as handle:
            handle.write(b"extra")

        report = find_duplicates(records)

        self.assertEqual(len(report.errors), 1)
        self.assertIn("changed since scan", report.errors[0])
        self.assertEqual(report.duplicate_files, 4)
        self.assertEqual(report.redundant_bytes, len(A) + len(B))

    def test_symlink_is_never_hashed_as_a_duplicate(self) -> None:
        link = self.root / "link_to_a1.txt"
        try:
            os.symlink(self.root / "a1.txt", link)
        except (OSError, NotImplementedError):
            self.skipTest("symlinks not available on this platform")

        records = self.scan()
        link_record = next(r for r in records if r.name == "link_to_a1.txt")
        # Force the link into the 6000-byte candidate bucket to exercise the guard.
        forged = [dataclasses.replace(link_record, size_bytes=len(A)) if r is link_record else r for r in records]

        report = find_duplicates(forged)

        grouped = {f.name for g in report.groups for f in g.files}
        self.assertNotIn("link_to_a1.txt", grouped)
        self.assertTrue(any("link_to_a1.txt" in e and "not a regular file" in e for e in report.errors))
        self.assertEqual(report.redundant_bytes, EXPECTED_REDUNDANT_BYTES)

    # ------------------------------------------------------------- read-only

    def snapshot(self) -> dict[str, tuple[int, int, bytes]]:
        state = {}
        for path in sorted(self.root.rglob("*")):
            info = path.lstat()
            content = path.read_bytes() if path.is_file() else b""
            state[str(path.relative_to(self.root))] = (info.st_size, info.st_mtime_ns, content)
        return state

    def test_detection_is_read_only(self) -> None:
        records = self.scan()
        before = self.snapshot()
        find_duplicates(records)
        self.assertEqual(self.snapshot(), before)


if __name__ == "__main__":
    unittest.main()
