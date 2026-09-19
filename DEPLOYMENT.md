# DIGITAL LANDFILL — PRODUCTION DEPLOYMENT GUIDE

This document outlines the architecture, environment variables, security safeguards, and deployment instructions for running **Digital Landfill** locally or on cloud infrastructure (e.g. Render, Vercel, Railway).

---

## 1. Architectural Overview & Modes

Digital Landfill supports two distinct operational modes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            MODE 1: LOCAL MODE                               │
│                                                                             │
│  React UI (Localhost:5173) ──► FastAPI (Localhost:8000) ──► C:\ Windows Disk│
│                                                                             │
│  - Full local filesystem access across user storage directories.           │
│  - Controlled pre-verified file deletion within scanned root.              │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                        MODE 2: DEPLOYED DEMO MODE                           │
│                                                                             │
│  Vercel/Render Frontend ──► Render Web Service ──► Bundled Demo Datasets   │
│                                                     (test_waste_sample/)    │
│                                                                             │
│  - Cloud servers cannot directly access a remote user's Windows drive.      │
│  - Arbitrary server filesystem paths are strictly rejected (HTTP 403).     │
│  - Operates safely on bundled demo fixtures with transparent UI badges.     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Environment Variables Reference

### Backend (`FastAPI`) Environment Variables

| Variable | Mode | Default | Description |
| :--- | :--- | :--- | :--- |
| `DEPLOYMENT_MODE` | Both | `local` | Set to `demo` (or `cloud`) in production cloud deployments to enforce filesystem sandboxing. Set to `local` on local machines. |
| `PORT` | Production | `8000` | Port to bind. Provided automatically by Render, Railway, etc. |
| `FRONTEND_ORIGIN` | Production | *(empty)* | Allowed origins for CORS (e.g. `https://digital-landfill.vercel.app,https://yourdomain.com`). When empty, allows all local `localhost` and `127.0.0.1` ports. |
| `DEMO_DIR` | Demo Mode | `test_waste_sample` | Default demo dataset folder auto-loaded on startup in Demo Mode. |
| `AI_KEY` | Both | *(required for Qwen)* | TCET Centre of Excellence AI Gateway API Key. **Never exposed to frontend**. |
| `QWEN_BASE_URL` | Both | `https://ai.tcetcercd.in/v1` | TCET CoE Gateway endpoint. |
| `QWEN_MODEL` | Both | `qwen3.6` | Qwen model identifier (`Qwen3.6-35B-A3B`). |

### Frontend (`Vite + React`) Environment Variables

| Variable | Mode | Default | Description |
| :--- | :--- | :--- | :--- |
| `VITE_API_BASE_URL` | Both | `http://127.0.0.1:8000` | URL of the running FastAPI backend. In production, set to your deployed backend URL (e.g. `https://digital-landfill-api.onrender.com`). |

---

## 3. Local Development (Mode 1)

### Quick 1-Click Launch
```powershell
python run.py
```
*(Automatically starts FastAPI on `http://127.0.0.1:8000`, Vite on `http://127.0.0.1:5173`, and opens your default web browser.)*

### Manual Launch (Two Terminals)

**Terminal 1 — Backend:**
```powershell
python -m uvicorn backend.api:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — Frontend:**
```powershell
cd frontend
npm install
npm run dev
```

---

## 4. Backend Cloud Deployment (Render / Railway / Fly.io)

### Render Web Service Setup

1. **New Web Service** pointing to your repository.
2. **Runtime:** Python 3.
3. **Build Command:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Start Command:**
   ```bash
   uvicorn backend.api:app --host 0.0.0.0 --port $PORT
   ```
5. **Environment Variables in Render Dashboard:**
   * `DEPLOYMENT_MODE` = `demo`
   * `FRONTEND_ORIGIN` = `https://your-frontend-domain.vercel.app`
   * `AI_KEY` = `your_tcet_coe_api_key`
   * `QWEN_BASE_URL` = `https://ai.tcetcercd.in/v1`
   * `QWEN_MODEL` = `qwen3.6`

---

## 5. Frontend Cloud Deployment (Vercel / Netlify / Render Static Site)

### Vercel / Netlify Setup

1. **Root Directory:** `frontend`
2. **Build Command:** `npm run build`
3. **Output Directory:** `dist`
4. **Environment Variables:**
   * `VITE_API_BASE_URL` = `https://your-backend-service.onrender.com` *(no trailing slash)*

---

## 6. Security & Safety Principles

1. **Zero Secret Leakage:**
   * `AI_KEY` and campus credentials remain securely inside the backend process and are never bundled into frontend static assets.
2. **Filesystem Sandboxing in Demo Mode:**
   * In Demo Mode (`DEPLOYMENT_MODE=demo`), `/api/scan` rejects any path outside the bundled demo datasets (`test_waste_sample/`). Arbitrary server paths (e.g. `/etc`, `/var`, `C:\Windows`) are rejected with `HTTP 403 Forbidden`.
3. **Pre-Verified Deletions (`/api/delete`):**
   * Even in local mode, deletions require explicit user confirmation (`confirmed: true`) and pre-verify disk existence, byte size, and timestamp immediately prior to removal.
   * AI reasoning models can never autonomously trigger deletions.
4. **Offline Resilience:**
   * If the TCET CoE Gateway is unreachable or unconfigured, all Phase 1–4 intelligence (inventory, duplicates, waste analysis, recovery simulator, recommendations) continues functioning normally.

---

## 7. Automated Verification

Before deploying, verify all automated tests locally:

```powershell
# Run core intelligence tests (66 tests)
python -m unittest discover -s src -v

# Run FastAPI backend API & deployment mode tests (9 tests)
python -m unittest backend.test_api -v

# Run frontend production build (TypeScript & bundle validation)
cd frontend
npm run build
```
