from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass(slots=True)
class FileRecord:
    name: str
    path: str
    parent: str
    extension: str
    category: str
    size_bytes: int
    size_label: str
    created_at: str
    modified_at: str
    accessed_at: str
    mime_type: str
    modified_timestamp: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


def format_timestamp(value: float | None) -> str:
    if value is None:
        return "—"
    try:
        if value <= 0:
            return "—"
        return datetime.fromtimestamp(value).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return "—"


def format_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(size)} {unit}"
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{num_bytes} B"
