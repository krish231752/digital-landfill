from __future__ import annotations

from collections import Counter

import pandas as pd

from src.models import FileRecord, format_size


def records_to_frame(records: list[FileRecord]) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(
            columns=[
                "name",
                "category",
                "extension",
                "size_label",
                "modified_at",
                "created_at",
                "mime_type",
                "parent",
                "path",
                "size_bytes",
            ]
        )
    return pd.DataFrame([r.to_dict() for r in records])


def summarize(records: list[FileRecord]) -> dict:
    total_files = len(records)
    total_bytes = sum(r.size_bytes for r in records)
    categories = Counter(r.category for r in records)
    extensions = Counter(r.extension for r in records)
    largest = max(records, key=lambda r: r.size_bytes, default=None)
    oldest = min(records, key=lambda r: r.modified_at, default=None)

    return {
        "total_files": total_files,
        "total_size_label": format_size(total_bytes),
        "total_bytes": total_bytes,
        "category_count": len(categories),
        "top_category": categories.most_common(1)[0][0] if categories else "—",
        "top_extension": extensions.most_common(1)[0][0] if extensions else "—",
        "largest_file": largest.name if largest else "—",
        "largest_size": largest.size_label if largest else "—",
        "oldest_modified": oldest.modified_at if oldest else "—",
        "categories": dict(categories.most_common()),
        "extensions": dict(extensions.most_common(8)),
    }
