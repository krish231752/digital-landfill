"""Exact duplicate detection (Phase 2).

Two files are duplicates when their contents are byte-for-byte identical, which
we decide by SHA-256. The module is strictly read-only: files are opened in
binary read mode and hashed in fixed-size chunks. Nothing is written, moved or
deleted.

Pipeline
--------
1. Bucket the scanner's records by ``size_bytes``. Identical files must have
   identical sizes, so a file with a unique size can never be a duplicate and
   is never read.
2. Hash every remaining candidate with SHA-256, streaming through a single
   reusable buffer so memory use does not depend on file size.
3. Group candidates that share a digest. Groups of one are discarded.
"""

from __future__ import annotations

import hashlib
import os
import stat
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable, Iterable

from src.models import FileRecord, format_size

CHUNK_SIZE = 1024 * 1024  # 1 MiB read buffer

# progress(done, total) -> None, called after each candidate file is handled.
ProgressCallback = Callable[[int, int], None]


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    """Files that share one SHA-256 digest (and therefore one size)."""

    sha256: str
    size_bytes: int
    files: tuple[FileRecord, ...]

    @property
    def file_count(self) -> int:
        return len(self.files)

    @property
    def redundant_files(self) -> int:
        """Copies beyond the one that would need to be kept."""
        return len(self.files) - 1

    @property
    def total_bytes(self) -> int:
        return self.size_bytes * len(self.files)

    @property
    def redundant_bytes(self) -> int:
        return self.size_bytes * (len(self.files) - 1)

    @property
    def total_size_label(self) -> str:
        return format_size(self.total_bytes)

    @property
    def redundant_size_label(self) -> str:
        return format_size(self.redundant_bytes)


@dataclass(slots=True)
class DuplicateReport:
    """Result of one duplicate-detection run."""

    groups: list[DuplicateGroup] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    candidate_files: int = 0  # files that shared a size with at least one other
    hashed_files: int = 0  # candidates that were hashed successfully
    bytes_hashed: int = 0  # bytes read from successfully hashed candidates

    @property
    def group_count(self) -> int:
        return len(self.groups)

    @property
    def duplicate_files(self) -> int:
        """Every file that belongs to a group (originals and copies)."""
        return sum(g.file_count for g in self.groups)

    @property
    def redundant_files(self) -> int:
        """Files beyond one per group."""
        return sum(g.redundant_files for g in self.groups)

    @property
    def redundant_bytes(self) -> int:
        """Storage held by every copy beyond one per group."""
        return sum(g.redundant_bytes for g in self.groups)

    @property
    def redundant_size_label(self) -> str:
        return format_size(self.redundant_bytes)


class _SkipFile(Exception):
    """A candidate that must not be trusted; the message is the reason."""


def hash_file(path: str | os.PathLike[str], chunk_size: int = CHUNK_SIZE) -> tuple[str, int]:
    """Return ``(sha256_hex, bytes_read)`` for a file, streamed in chunks.

    A single ``chunk_size`` buffer is reused for the whole file, so peak memory
    is about ``chunk_size`` no matter how large the file is.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    digest = hashlib.sha256()
    total = 0
    buffer = bytearray(chunk_size)
    view = memoryview(buffer)
    with open(path, "rb", buffering=0) as handle:
        while True:
            read = handle.readinto(view)
            if not read:
                break
            digest.update(view[:read])
            total += read
    return digest.hexdigest(), total


def _hash_record(record: FileRecord, chunk_size: int) -> str:
    """Hash one scanned file, refusing anything that is no longer what we scanned."""
    if not stat.S_ISREG(os.lstat(record.path).st_mode):
        # Symlinks would be hashed through to their target while occupying no
        # storage of their own, which would corrupt the redundant-size figure.
        raise _SkipFile("not a regular file (symlink or special file)")

    digest, bytes_read = hash_file(record.path, chunk_size)
    if bytes_read != record.size_bytes:
        raise _SkipFile(
            f"changed since scan (expected {record.size_bytes} bytes, read {bytes_read})"
        )
    return digest


def find_duplicates(
    records: Iterable[FileRecord],
    *,
    min_size_bytes: int = 1,
    chunk_size: int = CHUNK_SIZE,
    progress: ProgressCallback | None = None,
) -> DuplicateReport:
    """Find byte-identical files among scanned records. Never modifies files.

    ``min_size_bytes`` defaults to 1, which leaves out zero-byte files: they are
    trivially identical to each other but free up no storage. Pass 0 to include
    them.
    """
    report = DuplicateReport()

    by_size: dict[int, list[FileRecord]] = defaultdict(list)
    for record in records:
        if record.size_bytes >= min_size_bytes:
            by_size[record.size_bytes].append(record)

    candidates = [r for bucket in by_size.values() if len(bucket) > 1 for r in bucket]
    candidates.sort(key=lambda r: (r.size_bytes, r.path))
    report.candidate_files = len(candidates)

    by_digest: dict[str, list[FileRecord]] = defaultdict(list)
    total = len(candidates)
    for done, record in enumerate(candidates, start=1):
        try:
            digest = _hash_record(record, chunk_size)
        except FileNotFoundError:
            report.errors.append(f"{record.path}: disappeared during hashing")
        except PermissionError:
            report.errors.append(f"{record.path}: permission denied")
        except _SkipFile as exc:
            report.errors.append(f"{record.path}: {exc}")
        except OSError as exc:
            report.errors.append(f"{record.path}: {exc.strerror or exc}")
        else:
            by_digest[digest].append(record)
            report.hashed_files += 1
            report.bytes_hashed += record.size_bytes

        if progress is not None:
            progress(done, total)

    for digest, members in by_digest.items():
        if len(members) > 1:
            members.sort(key=lambda r: r.path)
            report.groups.append(
                DuplicateGroup(
                    sha256=digest,
                    size_bytes=members[0].size_bytes,
                    files=tuple(members),
                )
            )

    # Biggest storage win first; digest breaks ties so the order is deterministic.
    report.groups.sort(key=lambda g: (-g.redundant_bytes, -g.file_count, g.sha256))
    return report
