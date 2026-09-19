from __future__ import annotations

import mimetypes
import os
from pathlib import Path

from src.models import FileRecord, format_size, format_timestamp

CATEGORY_BY_EXT = {
    # Documents
    "pdf": "Documents",
    "doc": "Documents",
    "docx": "Documents",
    "txt": "Documents",
    "md": "Documents",
    "rtf": "Documents",
    "odt": "Documents",
    "tex": "Documents",
    "epub": "Documents",
    "pages": "Documents",
    # Images
    "jpg": "Images",
    "jpeg": "Images",
    "png": "Images",
    "gif": "Images",
    "bmp": "Images",
    "webp": "Images",
    "svg": "Images",
    "heic": "Images",
    "ico": "Images",
    "tiff": "Images",
    "tif": "Images",
    # Videos
    "mp4": "Videos",
    "mov": "Videos",
    "avi": "Videos",
    "mkv": "Videos",
    "webm": "Videos",
    "wmv": "Videos",
    "flv": "Videos",
    "m4v": "Videos",
    "3gp": "Videos",
    # Audio
    "mp3": "Audio",
    "wav": "Audio",
    "flac": "Audio",
    "aac": "Audio",
    "ogg": "Audio",
    "m4a": "Audio",
    "wma": "Audio",
    "opus": "Audio",
    "aiff": "Audio",
    # Archives
    "zip": "Archives",
    "rar": "Archives",
    "7z": "Archives",
    "tar": "Archives",
    "gz": "Archives",
    "bz2": "Archives",
    "xz": "Archives",
    "tgz": "Archives",
    "iso": "Archives",
    "dmg": "Archives",
    # Code
    "py": "Code",
    "js": "Code",
    "ts": "Code",
    "java": "Code",
    "c": "Code",
    "cpp": "Code",
    "cc": "Code",
    "cxx": "Code",
    "h": "Code",
    "hpp": "Code",
    "cs": "Code",
    "go": "Code",
    "rs": "Code",
    "html": "Code",
    "htm": "Code",
    "css": "Code",
    "scss": "Code",
    "sass": "Code",
    "less": "Code",
    "jsx": "Code",
    "tsx": "Code",
    "sql": "Code",
    "sh": "Code",
    "bash": "Code",
    "zsh": "Code",
    "ps1": "Code",
    "bat": "Code",
    "cmd": "Code",
    "json": "Code",
    "xml": "Code",
    "yml": "Code",
    "yaml": "Code",
    "toml": "Code",
    "ini": "Code",
    "cfg": "Code",
    "php": "Code",
    "rb": "Code",
    "swift": "Code",
    "kt": "Code",
    "r": "Code",
    # Datasets
    "parquet": "Datasets",
    "feather": "Datasets",
    "h5": "Datasets",
    "hdf5": "Datasets",
    "arrow": "Datasets",
    "csv": "Datasets",
    "tsv": "Datasets",
    "tab": "Datasets",
    "jsonl": "Datasets",
    "ndjson": "Datasets",
    "dta": "Datasets",
    "sav": "Datasets",
    # Presentations
    "ppt": "Presentations",
    "pptx": "Presentations",
    "odp": "Presentations",
    "key": "Presentations",
    # Spreadsheets
    "xls": "Spreadsheets",
    "xlsx": "Spreadsheets",
    "ods": "Spreadsheets",
    "numbers": "Spreadsheets",
}


def categorize(extension: str, custom_mapping: dict[str, str] | None = None) -> str:
    cleaned = extension.lower().lstrip(".")
    if custom_mapping and cleaned in custom_mapping:
        return custom_mapping[cleaned]
    return CATEGORY_BY_EXT.get(cleaned, "Other")


def _append_error(errors: list[str], location: object, reason: object) -> None:
    errors.append(f"{location}: {reason}")


def is_hidden(path: Path) -> bool:
    name = path.name
    if name.startswith("."):
        return True
    try:
        attrs = os.stat(path, follow_symlinks=False).st_file_attributes  # type: ignore[attr-defined]
        return bool(attrs & 2)  # FILE_ATTRIBUTE_HIDDEN on Windows
    except (AttributeError, FileNotFoundError, PermissionError, OSError):
        return False


def scan_folder(
    root: str | Path,
    *,
    skip_hidden: bool = True,
    max_files: int | None = None,
) -> tuple[list[FileRecord], list[str]]:
    """Walk a folder and collect file metadata. Never modifies or deletes files."""
    records: list[FileRecord] = []
    errors: list[str] = []

    try:
        root_path = Path(root).expanduser().resolve()
    except OSError as exc:
        _append_error(errors, root, exc)
        return records, errors

    if not root_path.exists() or not root_path.is_dir():
        raise ValueError("Selected path is not an existing folder.")

    def on_walk_error(err: OSError) -> None:
        location = getattr(err, "filename", None) or root_path
        if isinstance(err, PermissionError):
            _append_error(errors, location, "permission denied")
        elif isinstance(err, FileNotFoundError):
            _append_error(errors, location, "disappeared during scan")
        else:
            _append_error(errors, location, err)

    try:
        walker = os.walk(root_path, followlinks=False, onerror=on_walk_error)
    except OSError as exc:
        on_walk_error(exc)
        return records, errors

    for dirpath, dirnames, filenames in walker:
        try:
            current = Path(dirpath)
            if skip_hidden:
                kept: list[str] = []
                for dirname in dirnames:
                    child = current / dirname
                    try:
                        if not is_hidden(child):
                            kept.append(dirname)
                    except (FileNotFoundError, PermissionError, OSError) as exc:
                        _append_error(errors, child, _describe_os_error(exc))
                dirnames[:] = kept

            for filename in filenames:
                file_path = current / filename
                try:
                    if skip_hidden and is_hidden(file_path):
                        continue
                    records.append(_to_record(file_path))
                except FileNotFoundError:
                    _append_error(errors, file_path, "disappeared during scan")
                except PermissionError:
                    _append_error(errors, file_path, "permission denied")
                except OSError as exc:
                    _append_error(errors, file_path, _describe_os_error(exc))
                except (TypeError, ValueError, OverflowError) as exc:
                    _append_error(errors, file_path, f"unreadable metadata ({exc})")
                except Exception as exc:
                    _append_error(errors, file_path, exc)

                if max_files and len(records) >= max_files:
                    return records, errors
        except Exception as exc:
            _append_error(errors, dirpath, exc)

    return records, errors


def _describe_os_error(exc: OSError) -> str:
    if isinstance(exc, PermissionError):
        return "permission denied"
    if isinstance(exc, FileNotFoundError):
        return "disappeared during scan"
    return str(exc.strerror or exc)


def _to_record(path: Path) -> FileRecord:
    try:
        stats = path.stat(follow_symlinks=False)
    except TypeError:
        stats = path.stat()

    try:
        size_bytes = int(stats.st_size)
        if size_bytes < 0:
            raise ValueError(f"invalid size {size_bytes}")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"unreadable size metadata ({exc})") from exc

    try:
        extension = path.suffix.lower()
    except (TypeError, ValueError):
        extension = ""

    try:
        mime_type, _ = mimetypes.guess_type(str(path))
    except Exception:
        mime_type = None

    try:
        mtime = float(getattr(stats, "st_mtime", 0.0) or 0.0)
    except (TypeError, ValueError):
        mtime = 0.0

    return FileRecord(
        name=path.name,
        path=str(path),
        parent=str(path.parent),
        extension=extension or "—",
        category=categorize(extension),
        size_bytes=size_bytes,
        size_label=format_size(size_bytes),
        created_at=format_timestamp(getattr(stats, "st_ctime", None)),
        modified_at=format_timestamp(getattr(stats, "st_mtime", None)),
        accessed_at=format_timestamp(getattr(stats, "st_atime", None)),
        mime_type=mime_type or "unknown",
        modified_timestamp=mtime,
    )
