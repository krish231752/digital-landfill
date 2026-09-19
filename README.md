# DIGITAL LANDFILL

AI-powered digital waste intelligence and knowledge recovery. Local-first Streamlit dashboard that scans folders, extracts file metadata, analyzes storage waste patterns, detects exact byte-level duplicates, simulates storage recovery potential, and generates explainable, evidence-based review recommendations without modifying user files.

> **Safety Guarantee**: The application is strictly analysis-only. It never automatically deletes, moves, renames, uploads, or modifies files.

---

## Architecture & Stack

- **Frontend (`frontend/`):** React 19 + TypeScript + Vite + Tailwind CSS (presentation and control layer)
- **Backend Bridge (`backend/api.py`):** FastAPI + Uvicorn REST API on `http://127.0.0.1:8000`
- **Core Intelligence (`src/`):** Python local-first scanning, SHA-256 duplicate detection, waste analytics, recommendations, and TCET CoE Qwen AI gateway integration.

---

## Run Unified Application (React + FastAPI)

### 1. Start the FastAPI Backend
```powershell
cd digital-landfill
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

### 2. Start the React Frontend
```powershell
cd frontend
npm install
npm run dev
```

Open **`http://127.0.0.1:5173/`** in your browser.

*(Optional fallback: Streamlit legacy dashboard remains accessible via `streamlit run app.py`.)*

---

## Tests

Run the complete test suite across `src/` and `backend/`:

```powershell
python -m unittest discover -s src -v
python -m unittest discover -s backend -v
```

## Phase 1: File Intelligence

- Local folder scanning using non-recursive/recursive `os.walk` and `os.stat`.
- File metadata extraction (size, creation, modification, access time, MIME type).
- Interactive file inventory with search, extension filters, and category breakdowns.
- Pure metadata inspection without loading full files into memory.

---

## Phase 2: Exact Duplicate Detection

After scanning, click **Find exact duplicates** in the *Exact Duplicates* tab. Files are grouped when their SHA-256 hashes match, meaning they are byte-for-byte identical.

- **Candidate Pre-filtering**: Only files sharing identical sizes are candidate-hashed, skipping unique files.
- **Streaming Hashing**: Candidates are streamed in 1 MiB chunks with a single reusable buffer to protect memory.
- **Redundant Calculation**: Redundant size is computed as `size × (file_count − 1)`.
- **Fault-Tolerant**: Files that change, vanish, or lack read permissions during hashing are cleanly skipped and reported.

---

## Phase 3: Waste Intelligence

- **File Categorization**: Automatically categorizes files into Documents, Images, Videos, Audio, Archives, Code, Datasets, Presentations, Spreadsheets, or Other.
- **Storage Distribution**: Computes dynamic total storage, file count, and percentages per category with interactive bar charts.
- **Large File Intelligence**: Flags files exceeding a configurable size threshold (default: 100 MB), sorted descending by size.
- **Potentially Stale File Intelligence**: Identifies files older than a configurable threshold (default: 180 days) based on modification timestamps. Terminology is strictly neutral ("review candidates").
- **Temporary / Cache-like Detection**: Heuristic detection for temporary extensions (`.tmp`, `.temp`, `.bak`, `.log`, `.swp`, `.pyc`), lock patterns (`~$`), and cache directory paths (`__pycache__`, `.cache`, `temp`).
- **Exact Duplicate Waste**: Integrates Phase 2 duplicate metrics (`sum(size × (count - 1))`) directly into overall storage analytics.
- **Waste Indicator**: Transparent analytical score (`LOW`, `MEDIUM`, `HIGH`) derived from duplicate ratio, temporary file volume, and stale candidate density.
- **Storage Recovery Simulator**: Interactive 3-tier potential recovery calculator with cross-tier deduplication.

---

## Phase 4: AI-Powered Waste Recommendations

Phase 4 moves from detecting digital waste to understanding waste signals and providing structured, explainable, evidence-based recommendations.

- **Recommendation Types**:
  - `Exact Duplicate Review`: Multiple byte-identical copies detected via SHA-256.
  - `High Recovery Opportunity`: Major duplicate groups where manual review recovers significant storage.
  - `Large File Review`: Heavy assets consuming significant storage capacity.
  - `Potentially Stale File Review`: Dormant files untouched for extended periods.
  - `Temporary / Cache Candidate`: Heuristic matches for caches, logs, backups, and temporary files.
  - `Mixed Waste Signals Review`: Candidates exhibiting intersecting waste signals (e.g. large + stale + temporary).
- **Explainable Review Priority**: Recommendations are ranked by transparent priority rules (`HIGH`, `MEDIUM`, `LOW`) combining recoverable bytes, duplicate certainty, and signal convergence.
- **Evidence Confidence**: Transparent confidence indicators (`HIGH`, `MEDIUM`, `LOW`) reflecting the empirical strength of available evidence (e.g. SHA-256 certainty vs keyword heuristics).
- **Explainability Framework**: Every recommendation provides:
  - *Why this was flagged*: Clear bulleted checklist of detected signals.
  - *Potential impact*: Concrete storage recovery or reclamation estimate.
  - *Suggested action*: Actionable human-in-the-loop review instructions.
- **Human-in-the-Loop & Privacy Preserving**: Strictly local execution. No file uploads, no cloud APIs, and zero automatic deletions.

> *Note: The current Phase 4 recommendation engine is explainable and evidence-based. It does not automatically delete, move, rename, or modify files.*

---

## Phase 5: TCET CoE Qwen AI Integration

Phase 5 integrates the **TCET Centre of Excellence campus AI Gateway** using the **Qwen3.6** model (`Qwen3.6-35B-A3B`) as an AI reasoning and natural-language intelligence layer on top of the deterministic Phase 1–4 foundation.

- **Gateway Configuration**:
  - **Base URL**: `https://ai.tcetcercd.in/v1` (configurable via `QWEN_BASE_URL`)
  - **Model**: `qwen3.6` (configurable via `QWEN_MODEL`)
  - **SDK**: `openai` Python SDK (OpenAI-compatible protocol)
  - **Authentication**: `AI_KEY` loaded from `.env` or environment variables (never hardcoded, masked in UI)
- **AI-Powered Synthesis & Reasoning**:
  - **Executive Waste Analysis**: Synthesizes total scanned storage, waste index, duplicate redundancies, stale candidates, and storage recovery opportunities into actionable narrative insights.
  - **Recommendation Deep Dives**: Per-recommendation `💡 Explain with Qwen` button providing structured justifications, risk assessments, and step-by-step human review guidance.
  - **Live Streaming**: Real-time token streaming with live rendering for immediate feedback.
  - **Deep Reasoning Mode**: Optional deep-reasoning mode with step-by-step chain-of-thought analysis for complex waste structures.
- **Ask Digital Landfill (Grounded Interactive Assistant)**:
  - Natural-language Q&A grounded strictly in the active Phase 1–4 scan context.
  - Answers specific user questions: e.g. *"What are my top duplicates?"*, *"Which category consumes the most storage?"*, *"Can I safely review temp files?"*.
  - Quick-prompt suggestions for 1-click exploratory queries.
  - Multi-turn conversation support with context memory.
  - Transparent Context Inspector allowing users to inspect the exact sanitized evidence passed to Qwen.
- **Privacy & Security Guarantees**:
  - **No File Contents Uploaded**: Qwen receives only sanitized, structural metadata (aggregate counts, file sizes, categories, truncated relative paths).
  - **Deterministic Source of Truth**: Phase 1–4 metrics remain the strict ground truth; Qwen never modifies data, numbers, or records.
  - **Zero-Modification Guarantee**: Strictly read-only; no automatic file moves, renames, or deletions.
  - **Resilient Fallback**: Seamless offline degradation and user-friendly error banners for 401 (invalid key), 400 (bad request), 502 (gateway down), timeouts, and missing configurations.

---

## Configuration

Create a `.env` file in the project root:

```env
AI_KEY=your_tcet_coe_api_key_here
QWEN_BASE_URL=https://ai.tcetcercd.in/v1
QWEN_MODEL=qwen3.6
```

---

## Tests

Run the full automated test suite (using Python standard library `unittest`):

```powershell
python -m unittest -v
```

All tests operate with temporary, self-cleaning test directories and mock fixtures.

