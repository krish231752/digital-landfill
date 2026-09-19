import os
import time
from pathlib import Path

root = Path("test_waste_sample").resolve()
root.mkdir(exist_ok=True)

# Documents
(root / "documents").mkdir(exist_ok=True)
(root / "documents" / "quarterly_report.pdf").write_bytes(b"PDF-1.4 SAMPLE REPORT " * 1000)
(root / "documents" / "notes.txt").write_bytes(b"Project notes and meeting minutes\n" * 50)
(root / "documents" / "readme.md").write_bytes(b"# Project Readme\nMarkdown content here\n" * 30)

# Images
(root / "images").mkdir(exist_ok=True)
(root / "images" / "header.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"IMAGE_DATA" * 500)
(root / "images" / "profile.jpg").write_bytes(b"\xff\xd8\xff" + b"JPEG_DATA" * 300)

# Code
(root / "code").mkdir(exist_ok=True)
(root / "code" / "pipeline.py").write_bytes(b"import os\nprint('Processing pipeline')\n" * 100)
(root / "code" / "app.ts").write_bytes(b"export const config = { active: true };\n" * 50)

# Datasets
(root / "datasets").mkdir(exist_ok=True)
(root / "datasets" / "sales_data.csv").write_bytes(b"id,item,price,qty\n1,apple,1.5,10\n" * 2000)
(root / "datasets" / "metrics.parquet").write_bytes(b"PAR1" + b"DATA_BINARY" * 5000)

# Exact Duplicates (3 copies: 1 original + 2 redundant)
(root / "backup_duplicates").mkdir(exist_ok=True)
dup1 = b"EXACT_DUPLICATE_DATA_BLOCK_ALPHA" * 20000
(root / "documents" / "archive_alpha.bin").write_bytes(dup1)
(root / "backup_duplicates" / "archive_alpha_copy.bin").write_bytes(dup1)
(root / "backup_duplicates" / "archive_alpha_copy2.bin").write_bytes(dup1)

# Large file (105 MB)
large_block = b"0" * (1024 * 1024)
with open(root / "large_database_dump.iso", "wb") as f:
    for _ in range(105):
        f.write(large_block)

# Old / Stale file (> 250 days ago)
stale_file = root / "documents" / "old_contract_2022.pdf"
stale_file.write_bytes(b"OLD CONTRACT CONTENT FROM PAST YEAR" * 500)
old_time = time.time() - (250 * 86400)
os.utime(stale_file, (old_time, old_time))

# Temporary & Cache files
(root / "temp").mkdir(exist_ok=True)
(root / "temp" / "session_cache.tmp").write_bytes(b"TMP_CACHE_BYTES" * 1000)
(root / "temp" / "old_db_backup.bak").write_bytes(b"BAK_BYTES" * 1500)
(root / "documents" / "~$quarterly_report.docx").write_bytes(b"LOCK_FILE_HEADER" * 50)

cache_dir = root / "__pycache__"
cache_dir.mkdir(exist_ok=True)
(cache_dir / "pipeline.cpython-311.pyc").write_bytes(b"BYTECODE_DATA" * 400)

print(f"Created test fixture at {root}")
