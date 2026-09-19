"""Visual tokens for the Streamlit dashboard."""

CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --bg: #0f1412;
        --panel: #171e1b;
        --panel-2: #1e2723;
        --line: #2c3833;
        --text: #e8eee9;
        --muted: #9aaea4;
        --accent: #7cb89a;
        --accent-2: #c4b37a;
        --danger: #d48a7a;
    }

    .stApp {
        background:
            radial-gradient(1200px 500px at 10% -10%, #1c2a24 0%, transparent 55%),
            linear-gradient(180deg, #0f1412 0%, #121816 100%);
        color: var(--text);
        font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
    }

    header[data-testid="stHeader"] { background: transparent; }
    [data-testid="stSidebar"] {
        background: #121816;
        border-right: 1px solid var(--line);
    }

    .hero {
        padding: 0.4rem 0 1.2rem 0;
        border-bottom: 1px solid var(--line);
        margin-bottom: 1.4rem;
    }
    .kicker {
        font-family: "IBM Plex Mono", monospace;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        font-size: 0.72rem;
        color: var(--accent);
        margin-bottom: 0.35rem;
    }
    .hero h1 {
        font-size: 2.1rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        margin: 0;
        color: var(--text);
    }
    .hero p {
        color: var(--muted);
        margin: 0.45rem 0 0 0;
        max-width: 46rem;
        line-height: 1.5;
    }

    .metric-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0.85rem;
        margin: 0.4rem 0 1.2rem 0;
    }
    .metric-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 1rem 1.05rem 0.95rem 1.05rem;
        min-height: 96px;
    }
    .metric-card .label {
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.7rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--muted);
        margin-bottom: 0.45rem;
    }
    .metric-card .value {
        font-size: 1.55rem;
        font-weight: 650;
        color: var(--text);
        line-height: 1.15;
        word-break: break-word;
    }
    .metric-card .hint {
        margin-top: 0.35rem;
        color: var(--muted);
        font-size: 0.8rem;
    }

    .shell-row {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr 1fr;
        gap: 0.85rem;
        margin-bottom: 1.3rem;
    }
    .shell-card {
        background: var(--panel-2);
        border: 1px dashed var(--line);
        border-radius: 14px;
        padding: 0.95rem 1rem;
    }
    .shell-card h3 {
        margin: 0 0 0.3rem 0;
        font-size: 0.92rem;
        font-weight: 600;
    }
    .shell-card p {
        margin: 0;
        color: var(--muted);
        font-size: 0.8rem;
        line-height: 1.45;
    }
    .badge {
        display: inline-block;
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.65rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--accent-2);
        border: 1px solid #3d3824;
        background: #262318;
        border-radius: 999px;
        padding: 0.12rem 0.5rem;
        margin-bottom: 0.45rem;
    }

    .badge-low {
        color: #7cb89a;
        background: #182620;
        border: 1px solid #284437;
    }
    .badge-medium {
        color: #c4b37a;
        background: #262318;
        border: 1px solid #4a3f23;
    }
    .badge-high {
        color: #e58f80;
        background: #2e1c19;
        border: 1px solid #542f28;
    }

    .signal-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 12px;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.6rem;
        display: flex;
        align-items: flex-start;
        gap: 0.8rem;
    }
    .signal-card.high { border-left: 4px solid var(--danger); }
    .signal-card.medium { border-left: 4px solid var(--accent-2); }
    .signal-card.low { border-left: 4px solid var(--accent); }
    .signal-card.neutral { border-left: 4px solid var(--muted); }

    .signal-title {
        font-weight: 600;
        font-size: 0.9rem;
        color: var(--text);
        margin-bottom: 0.2rem;
    }
    .signal-detail {
        font-size: 0.82rem;
        color: var(--muted);
        line-height: 1.4;
    }

    .recovery-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 0.9rem;
        margin: 0.6rem 0 1.2rem 0;
    }
    .recovery-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 1.1rem;
    }
    .recovery-card.tier1 { border-top: 3px solid var(--accent); }
    .recovery-card.tier2 { border-top: 3px solid var(--accent-2); }
    .recovery-card.tier3 { border-top: 3px solid #9aaea4; }

    .recovery-tier-tag {
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.68rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: var(--accent);
        margin-bottom: 0.4rem;
    }
    .recovery-card.tier2 .recovery-tier-tag { color: var(--accent-2); }
    .recovery-card.tier3 .recovery-tier-tag { color: var(--muted); }

    .recovery-card h4 {
        margin: 0 0 0.4rem 0;
        font-size: 1.02rem;
        font-weight: 650;
    }
    .recovery-value {
        font-size: 1.7rem;
        font-weight: 700;
        color: var(--text);
        margin: 0.3rem 0;
    }
    .recovery-desc {
        color: var(--muted);
        font-size: 0.8rem;
        line-height: 1.45;
    }

    /* Phase 4: Recommendation Cards */
    .rec-card {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 1.15rem 1.25rem;
        margin-bottom: 1rem;
        transition: border-color 0.2s ease;
    }
    .rec-card.HIGH {
        border-left: 5px solid #e58f80;
    }
    .rec-card.MEDIUM {
        border-left: 5px solid #c4b37a;
    }
    .rec-card.LOW {
        border-left: 5px solid #7cb89a;
    }

    .rec-top-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 0.5rem;
        margin-bottom: 0.6rem;
    }
    .rec-badges {
        display: flex;
        gap: 0.45rem;
        align-items: center;
        flex-wrap: wrap;
    }
    .rec-title {
        font-size: 1.12rem;
        font-weight: 650;
        color: var(--text);
        margin: 0.2rem 0 0.5rem 0;
    }
    .rec-recovery-highlight {
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.88rem;
        color: var(--accent);
        background: #17241e;
        border: 1px solid #284437;
        border-radius: 8px;
        padding: 0.25rem 0.6rem;
        font-weight: 600;
    }

    .rec-block-title {
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.7rem;
        letter-spacing: 0.09em;
        text-transform: uppercase;
        color: var(--muted);
        margin: 0.75rem 0 0.35rem 0;
        font-weight: 600;
    }

    .rec-reason-list {
        margin: 0;
        padding-left: 1.2rem;
        font-size: 0.86rem;
        color: var(--text);
        line-height: 1.5;
    }

    .rec-impact-box {
        background: #16201c;
        border: 1px solid #23332c;
        border-radius: 8px;
        padding: 0.6rem 0.85rem;
        font-size: 0.84rem;
        color: var(--text);
        margin-top: 0.3rem;
    }

    .rec-action-box {
        background: #1c221c;
        border: 1px solid #2d382d;
        border-radius: 8px;
        padding: 0.6rem 0.85rem;
        font-size: 0.84rem;
        color: var(--accent);
        margin-top: 0.3rem;
    }

    /* Phase 5: TCET CoE Qwen AI Integration */
    .ai-container {
        background: #131c17;
        border: 1px solid #26382e;
        border-top: 4px solid var(--accent);
        border-radius: 14px;
        padding: 1.3rem 1.4rem;
        margin-bottom: 1.2rem;
    }
    .ai-status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.72rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        border-radius: 999px;
        padding: 0.2rem 0.65rem;
        font-weight: 600;
    }
    .ai-status-connected {
        color: #7cb89a;
        background: #172b20;
        border: 1px solid #2e4d3b;
    }
    .ai-status-unconfigured {
        color: #c4b37a;
        background: #2a2618;
        border: 1px solid #4a3f23;
    }
    .ai-status-offline {
        color: #e58f80;
        background: #2e1c19;
        border: 1px solid #542f28;
    }

    .ai-output-box {
        background: #151d19;
        border: 1px solid #233029;
        border-radius: 12px;
        padding: 1.2rem 1.3rem;
        color: var(--text);
        line-height: 1.6;
        font-size: 0.92rem;
        margin-top: 0.8rem;
    }
    .ai-output-box h2, .ai-output-box h3 {
        color: var(--accent);
        margin-top: 1rem;
        margin-bottom: 0.4rem;
    }

    .notice {
        background: #1a2420;
        border: 1px solid var(--line);
        color: var(--muted);
        border-radius: 12px;
        padding: 0.7rem 0.9rem;
        font-size: 0.85rem;
        margin-bottom: 1rem;
    }

    /* Ask Digital Landfill - Grounded Chat & Q&A */
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 0.9rem;
        margin-bottom: 1.2rem;
    }
    .chat-msg-user {
        background: #1e2a23;
        border: 1px solid #2d4236;
        border-radius: 12px 12px 2px 12px;
        padding: 0.9rem 1.1rem;
        color: var(--text);
        margin-left: 2rem;
        font-size: 0.92rem;
    }
    .chat-msg-assistant {
        background: #131c17;
        border: 1px solid #26382e;
        border-left: 4px solid var(--accent);
        border-radius: 12px 12px 12px 2px;
        padding: 1.1rem 1.3rem;
        color: var(--text);
        margin-right: 2rem;
        font-size: 0.92rem;
        line-height: 1.6;
    }
    .chat-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.4rem;
        font-size: 0.75rem;
        font-family: "IBM Plex Mono", monospace;
        color: var(--muted);
    }
    .grounding-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.3rem;
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.7rem;
        color: #7cb89a;
        background: #172b20;
        border: 1px solid #2e4d3b;
        border-radius: 999px;
        padding: 0.15rem 0.55rem;
    }
    .context-preview-box {
        background: #0d1410;
        border: 1px solid #1e2e25;
        border-radius: 8px;
        padding: 0.8rem;
        font-family: "IBM Plex Mono", monospace;
        font-size: 0.75rem;
        color: #8da497;
        max-height: 220px;
        overflow-y: auto;
        white-space: pre-wrap;
    }

    @media (max-width: 1100px) {
        .metric-grid, .shell-row, .recovery-grid { grid-template-columns: 1fr 1fr; }
    }
    @media (max-width: 700px) {
        .metric-grid, .shell-row, .recovery-grid { grid-template-columns: 1fr; }
    }
</style>
"""
