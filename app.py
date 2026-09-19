from __future__ import annotations

import time
from pathlib import Path

import pandas as pd
import streamlit as st

from src.duplicates import find_duplicates
from src.metrics import records_to_frame, summarize
from src.models import format_size
from src.qwen_client import QwenConfig, check_qwen_health
from src.qwen_service import (
    QwenService,
    build_grounded_scan_context,
    sanitize_evidence,
)
from src.recommendations import (
    TYPE_LABELS,
    Confidence,
    Priority,
    Recommendation,
    RecommendationType,
    generate_recommendations,
)
from src.scanner import scan_folder
from src.theme import CSS
from src.waste import (
    calculate_waste_score,
    find_large_files,
    find_stale_files,
    find_temp_cache_files,
    get_storage_distribution,
    simulate_recovery,
    summarize_duplicate_waste,
)

st.set_page_config(
    page_title="DIGITAL LANDFILL — TCET CoE AI Waste Intelligence",
    page_icon="🗂️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CSS, unsafe_allow_html=True)

# Session state initialization
if "records" not in st.session_state:
    st.session_state.records = []
    st.session_state.errors = []
    st.session_state.scanned_root = None
st.session_state.setdefault("duplicates", None)
st.session_state.setdefault("qwen_analysis", None)
st.session_state.setdefault("qwen_rec_explanations", {})
st.session_state.setdefault("chat_history", [])
st.session_state.setdefault("chat_prompt_to_run", None)


def metric_card(label: str, value: str, hint: str = "") -> str:
    hint_html = f'<div class="hint">{hint}</div>' if hint else ""
    return (
        f'<div class="metric-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div>{hint_html}</div>'
    )


# ---------------------------------------------------------------------------
# Sidebar Controls & Analysis Parameters
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Scan source")
    st.caption("Point at a local folder. Processing is strictly local and read-only.")
    with st.form("scan_form"):
        folder = st.text_input(
            "Folder path",
            value=str(Path.home()),
            placeholder=r"C:\Users\you\Documents",
        )
        skip_hidden = st.checkbox("Skip hidden files and folders", value=True)
        cap_enabled = st.checkbox("Limit number of files", value=False)
        max_files = st.number_input(
            "Maximum files",
            min_value=100,
            max_value=200_000,
            value=10_000,
            step=100,
        )
        scan_clicked = st.form_submit_button("Scan folder", type="primary", use_container_width=True)

    st.markdown("---")
    st.markdown("### Waste Analysis Thresholds")
    large_threshold_mb = st.number_input(
        "Large file threshold (MB)",
        min_value=1,
        max_value=10_000,
        value=100,
        step=10,
        help="Files at or above this size are flagged in Large File Intelligence.",
    )
    stale_days_threshold = st.number_input(
        "Stale file threshold (days)",
        min_value=7,
        max_value=3650,
        value=180,
        step=30,
        help="Files not modified within this many days are flagged as review candidates.",
    )

    st.markdown("---")
    st.markdown("### 🤖 TCET CoE AI Gateway")
    st.caption("Campus AI reasoning layer powered by Qwen3.6-35B-A3B.")

    # Check Gateway Health
    base_cfg = QwenConfig.from_env()
    is_healthy, health_badge, health_detail = check_qwen_health(base_cfg)

    st.markdown(
        f'<div class="ai-status-badge {"ai-status-connected" if is_healthy else "ai-status-unconfigured" if not base_cfg.api_key else "ai-status-offline"}">{health_badge}</div>',
        unsafe_allow_html=True,
    )
    st.caption(health_detail)

    sidebar_api_key = st.text_input(
        "AI Key (optional session override)",
        type="password",
        placeholder="Enter AI_KEY if not in .env",
        help="API Key is never printed or written to disk. Defaults to AI_KEY from .env.",
        key="session_ai_key",
    )
    effective_key = sidebar_api_key.strip() if sidebar_api_key.strip() else base_cfg.api_key
    qwen_config = QwenConfig.from_env(custom_key=effective_key)

    enable_thinking = st.checkbox(
        "Enable Qwen Deep Reasoning Mode",
        value=False,
        help="Enables extended analytical thinking inside Qwen (reasoning_effort: medium).",
    )
    qwen_config.enable_thinking = enable_thinking

    st.markdown("---")
    st.caption(
        "Safety Guarantee: This application is strictly analysis-only. It never automatically "
        "deletes, moves, renames, uploads, or modifies files."
    )

if scan_clicked:
    path = Path(folder.strip()) if folder else None
    if not path or not path.exists() or not path.is_dir():
        st.sidebar.error("Enter a valid existing folder path.")
    else:
        with st.spinner(f"Scanning {path} …"):
            records, errors = scan_folder(
                path,
                skip_hidden=skip_hidden,
                max_files=int(max_files) if cap_enabled else None,
            )
        st.session_state.records = records
        st.session_state.errors = errors
        st.session_state.scanned_root = str(path)
        st.session_state.duplicates = None
        st.session_state.qwen_analysis = None
        st.session_state.qwen_rec_explanations = {}

# ---------------------------------------------------------------------------
# Main Header
# ---------------------------------------------------------------------------

st.markdown(
    """
    <div class="hero">
        <div class="kicker">Phase 5 · TCET CoE Qwen AI Integration</div>
        <h1>DIGITAL LANDFILL</h1>
        <p>
            AI-powered digital waste intelligence and knowledge recovery.
            Combines local deterministic scanning, exact duplicate hashing, and waste analytics
            with natural-language reasoning from the TCET Centre of Excellence Qwen3.6 AI Gateway.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

records = st.session_state.records
summary = summarize(records)
root_name = Path(st.session_state.scanned_root).name if st.session_state.scanned_root else "scanned folder"
summary["root_name"] = root_name

if not records:
    st.info("👈 Enter a folder path in the sidebar and click **Scan folder** to begin.")
else:
    # -----------------------------------------------------------------------
    # Compute Core Analytics (Phase 1–4)
    # -----------------------------------------------------------------------
    large_threshold_bytes = int(large_threshold_mb * 1024 * 1024)
    cat_distribution = get_storage_distribution(records)
    large_report = find_large_files(records, threshold_bytes=large_threshold_bytes)
    stale_report = find_stale_files(records, days_threshold=int(stale_days_threshold))
    temp_report = find_temp_cache_files(records)
    dup_summary = summarize_duplicate_waste(st.session_state.duplicates)
    waste_score = calculate_waste_score(
        records=records,
        duplicate_report=st.session_state.duplicates,
        large_report=large_report,
        stale_report=stale_report,
        temp_report=temp_report,
    )
    recovery = simulate_recovery(
        records=records,
        duplicate_report=st.session_state.duplicates,
        temp_report=temp_report,
        stale_report=stale_report,
    )

    # Phase 4 AI Recommendation Engine
    rec_report = generate_recommendations(
        records=records,
        duplicate_report=st.session_state.duplicates,
        large_report=large_report,
        stale_report=stale_report,
        temp_report=temp_report,
        large_threshold_bytes=large_threshold_bytes,
        stale_days_threshold=int(stale_days_threshold),
    )

    # Phase 5 Qwen Service
    qwen_service = QwenService(config=qwen_config)

    # -----------------------------------------------------------------------
    # Top-Level Waste & AI Overview Metrics
    # -----------------------------------------------------------------------
    st.markdown(
        f"""
        <div class="metric-grid">
            {metric_card("Files scanned", f"{summary['total_files']:,}", st.session_state.scanned_root or "")}
            {metric_card("Total storage", summary["total_size_label"], f"{len(cat_distribution)} categories")}
            {metric_card("AI Recommendations", f"{rec_report.total_count:,}", f"{rec_report.high_count} High · {rec_report.medium_count} Med · {rec_report.low_count} Low")}
            {metric_card("Waste Indicator", waste_score.level, f"Score: {waste_score.score_value}/100 · Analytical signals")}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="metric-grid">
            {metric_card("Exact duplicate waste", dup_summary.redundant_size_label if dup_summary.has_run else "Not scanned", f"{dup_summary.redundant_files:,} redundant copies" if dup_summary.has_run else "Phase 2 duplicate search")}
            {metric_card("Large files", f"{large_report.count:,}", f"≥ {large_threshold_mb} MB · {large_report.total_size_label}")}
            {metric_card("Potentially stale", f"{stale_report.count:,}", f"> {stale_days_threshold} days · {stale_report.total_size_label}")}
            {metric_card("Temp / cache candidates", f"{temp_report.count:,}", f"Heuristics · {temp_report.total_size_label}")}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.errors:
        st.caption(f"⚠️ Skipped / unreadable files during scan: {len(st.session_state.errors):,}")

    # -----------------------------------------------------------------------
    # Interactive Tabs for Intelligence & Inventory
    # -----------------------------------------------------------------------
    tab_ask, tab_qwen, tab_rec, tab_dist, tab_large, tab_stale, tab_temp, tab_dup, tab_sim, tab_inv = st.tabs(
        [
            "💬 Ask Digital Landfill",
            "🤖 TCET CoE Qwen AI",
            f"💡 Recommendations ({rec_report.total_count})",
            "📊 Storage Distribution",
            f"🐘 Large Files ({large_report.count})",
            f"⏳ Potentially Stale ({stale_report.count})",
            f"🧹 Temp / Cache ({temp_report.count})",
            f"👥 Exact Duplicates ({dup_summary.group_count if dup_summary.has_run else '—'})",
            "💡 Recovery Simulator",
            "🗂️ Full Inventory",
        ]
    )

    # -----------------------------------------------------------------------
    # TAB 1: Ask Digital Landfill (Grounded AI Assistant)
    # -----------------------------------------------------------------------
    with tab_ask:
        st.subheader("💬 Ask Digital Landfill — Grounded AI Assistant")
        st.caption(
            "Interactive Q&A powered by TCET CoE Qwen (Qwen3.6-35B-A3B). "
            "Every answer is strictly grounded in your active Phase 1–4 scan context."
        )

        # Build grounded context
        scan_ctx = build_grounded_scan_context(
            summary=summary,
            cat_distribution=cat_distribution,
            duplicate_report=st.session_state.duplicates,
            large_report=large_report,
            stale_report=stale_report,
            temp_report=temp_report,
            rec_report=rec_report,
            recovery=recovery,
        )

        st.markdown(
            f"""
            <div class="notice" style="display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span class="grounding-badge">🔒 Grounded Context</span>
                    <span>Answering based on <strong>{summary.get('total_files', 0):,} files ({summary.get('total_size_label', '0 B')})</strong> in <code>{summary.get('root_name', root_name)}</code></span>
                </div>
                <div style="font-family:monospace;font-size:0.75rem;color:var(--muted);">
                    Gateway: {qwen_config.model}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Context inspector expander
        with st.expander("🔍 Inspect Grounded Scan Context (Sanitized Evidence sent to Qwen)", expanded=False):
            st.caption(
                "Verify the exact structured metadata provided to Qwen. "
                "Notice that zero file contents and zero private root paths are included."
            )
            st.markdown(f'<div class="context-preview-box">{scan_ctx}</div>', unsafe_allow_html=True)

        st.markdown("##### 💡 Quick Questions")
        qp_col1, qp_col2, qp_col3, qp_col4 = st.columns(4)

        prompt_to_submit = None

        with qp_col1:
            if st.button("🐘 Top Storage Hogs", key="qp_large", use_container_width=True):
                prompt_to_submit = "What are the largest files and categories taking up the most storage?"
        with qp_col2:
            if st.button("👥 Top Duplicates", key="qp_dup", use_container_width=True):
                prompt_to_submit = "Where are my top duplicate files and how much space can I safely recover?"
        with qp_col3:
            if st.button("🎯 Priority Recommendations", key="qp_rec", use_container_width=True):
                prompt_to_submit = "Summarize my highest priority waste recommendations and what actions I should take."
        with qp_col4:
            if st.button("🧹 Temp & Cache Review", key="qp_temp", use_container_width=True):
                prompt_to_submit = "Can I safely review or clean up temporary and cache files found in this scan?"

        # Action bar with Clear Chat button
        col_ctrl1, col_ctrl2 = st.columns((4, 1))
        with col_ctrl2:
            if st.session_state.chat_history:
                if st.button("🗑️ Clear Chat", key="btn_clear_chat", use_container_width=True):
                    st.session_state.chat_history = []
                    st.session_state.chat_prompt_to_run = None
                    st.rerun()

        # Render conversation history
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            elif msg["role"] == "assistant":
                with st.chat_message("assistant"):
                    st.markdown(msg["content"])

        # Chat Input
        user_input = st.chat_input("Ask anything about your scanned files, duplicates, or cleanup opportunities…")

        active_query = user_input or prompt_to_submit or st.session_state.chat_prompt_to_run
        if active_query:
            st.session_state.chat_prompt_to_run = None
            # Append user message
            st.session_state.chat_history.append({"role": "user", "content": active_query})
            with st.chat_message("user"):
                st.markdown(active_query)

            # Generate and stream assistant answer
            with st.chat_message("assistant"):
                with st.spinner("TCET CoE Qwen is reasoning over scan context…"):
                    stream_gen = qwen_service.ask_digital_landfill_stream(
                        query=active_query,
                        scan_context=scan_ctx,
                        chat_history=st.session_state.chat_history[:-1],
                    )
                    try:
                        reply_text = st.write_stream(stream_gen)
                        st.session_state.chat_history.append({"role": "assistant", "content": reply_text})
                    except Exception as exc:
                        st.error(f"Error communicating with TCET CoE Qwen Gateway: {exc}")

    # -----------------------------------------------------------------------
    # TAB 2: TCET CoE Qwen AI Intelligence (Phase 5)
    # -----------------------------------------------------------------------
    with tab_qwen:
        st.subheader("🤖 TCET CoE Qwen AI Waste Intelligence")
        st.caption(
            "Natural-language synthesis and reasoning powered by the TCET Centre of Excellence "
            "campus AI Gateway (Qwen3.6-35B-A3B). Synthesizes verified Phase 1–4 structured evidence."
        )

        st.markdown(
            f"""
            <div class="notice">
                <strong>Campus Gateway Configuration:</strong> Endpoint: <code>{qwen_config.base_url}</code> · Model: <code>{qwen_config.model}</code> · Reasoning: <code>{"Enabled (Medium)" if qwen_config.enable_thinking else "Standard"}</code>
                <br><em>Core Architecture Guarantee: Phase 1–4 local intelligence is the source of truth. Qwen contextualizes verified evidence and never hallucinates file facts.</em>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_btn1, col_btn2 = st.columns((2, 1))
        with col_btn1:
            run_ai = st.button("🚀 Analyze with TCET CoE Qwen", type="primary", key="btn_run_qwen")
        with col_btn2:
            if st.session_state.qwen_analysis:
                if st.button("🔄 Clear AI Analysis Cache", key="btn_clear_qwen"):
                    st.session_state.qwen_analysis = None
                    st.rerun()

        # Sanitize structured evidence for Qwen
        sanitized_ev = sanitize_evidence(
            summary=summary,
            cat_distribution=cat_distribution,
            duplicate_report=st.session_state.duplicates,
            large_report=large_report,
            stale_report=stale_report,
            temp_report=temp_report,
            rec_report=rec_report,
            recovery=recovery,
        )

        if run_ai:
            st.markdown("### 🧠 AI Reasoning in Progress…")
            stream_container = st.empty()
            with st.spinner("Connecting to TCET CoE AI Gateway…"):
                stream_generator = qwen_service.analyze_waste_stream(sanitized_ev)
                try:
                    analysis_text = stream_container.write_stream(stream_generator)
                    st.session_state.qwen_analysis = analysis_text
                except Exception as exc:
                    st.error(f"Error during AI streaming: {exc}")

        elif st.session_state.qwen_analysis:
            st.markdown(
                f"""
                <div class="ai-container">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.6rem;">
                        <span class="ai-status-badge ai-status-connected">✓ TCET CoE Qwen Analysis Ready</span>
                        <span style="font-size:0.78rem;color:var(--muted);font-family:monospace;">Model: {qwen_config.model}</span>
                    </div>
                    <div class="ai-output-box">
                        {st.session_state.qwen_analysis}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.info(
                "Click **🚀 Analyze with TCET CoE Qwen** to generate an executive AI summary, "
                "waste insights, prioritized review recommendations, and recovery explanations."
            )

        # Dual View: Verified Local Evidence alongside AI Interpretation
        with st.expander("🔍 View Structured Evidence Transmitted to Qwen (Privacy-Preserving)", expanded=False):
            st.caption("Only aggregate statistics and sanitized relative names are sent. No file contents are read or uploaded.")
            st.json(sanitized_ev)

    # -----------------------------------------------------------------------
    # TAB 2: AI Waste Recommendations (Phase 4 + Phase 5 Explain Action)
    # -----------------------------------------------------------------------
    with tab_rec:
        st.subheader("💡 AI Waste Review Recommendations")
        st.caption(
            "Explainable, evidence-based recommendations generated from scanned duplicate signals, "
            "file sizes, modification ages, and heuristic waste patterns. Ranked by Review Priority."
        )

        # Recommendation Summary Metrics
        st.markdown(
            f"""
            <div class="metric-grid">
                {metric_card("Total Recommendations", f"{rec_report.total_count:,}", "Ranked by review priority")}
                {metric_card("High Priority Reviews", f"{rec_report.high_count:,}", "Immediate review opportunities")}
                {metric_card("Medium Priority Reviews", f"{rec_report.medium_count:,}", "Moderate impact candidates")}
                {metric_card("Low Priority Reviews", f"{rec_report.low_count:,}", "Minor clutter candidates")}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Recommendation Filters
        st.markdown("##### Filter Recommendations")
        col_f1, col_f2, col_f3, col_f4 = st.columns((1, 1.5, 1, 2))
        with col_f1:
            pri_filter = st.selectbox("Priority", ["All", "HIGH", "MEDIUM", "LOW"], key="rec_pri_filter")
        with col_f2:
            type_options = ["All"] + list(TYPE_LABELS.values())
            type_filter = st.selectbox("Recommendation Type", type_options, key="rec_type_filter")
        with col_f3:
            conf_filter = st.selectbox("Evidence Confidence", ["All", "HIGH", "MEDIUM", "LOW"], key="rec_conf_filter")
        with col_f4:
            search_query = st.text_input("Search in recommendations", placeholder="file name, path, reason…", key="rec_search")

        # Apply Filters
        filtered_recs: list[Recommendation] = rec_report.recommendations
        if pri_filter != "All":
            filtered_recs = [r for r in filtered_recs if r.priority == pri_filter]
        if type_filter != "All":
            filtered_recs = [r for r in filtered_recs if r.type_label == type_filter]
        if conf_filter != "All":
            filtered_recs = [r for r in filtered_recs if r.confidence == conf_filter]
        if search_query.strip():
            sq = search_query.strip().lower()
            filtered_recs = [
                r
                for r in filtered_recs
                if sq in r.title.lower()
                or sq in r.target_name.lower()
                or sq in r.target_path.lower()
                or any(sq in reason.lower() for reason in r.reasons)
                or sq in r.impact_description.lower()
            ]

        st.caption(f"Showing {len(filtered_recs):,} of {rec_report.total_count:,} recommendations")

        if not filtered_recs:
            st.success("No recommendations match the current filter selection.")
        else:
            for idx, rec in enumerate(filtered_recs, start=1):
                pri_icon = "🔴" if rec.priority == "HIGH" else "🟡" if rec.priority == "MEDIUM" else "🟢"
                pri_badge_class = f"badge-{rec.priority.lower()}"
                conf_badge_class = f"badge-{rec.confidence.lower()}"

                st.markdown(
                    f"""
                    <div class="rec-card {rec.priority}">
                        <div class="rec-top-row">
                            <div class="rec-badges">
                                <span class="badge {pri_badge_class}">{pri_icon} {rec.priority} PRIORITY</span>
                                <span class="badge" style="color:var(--text);border-color:var(--line);background:#1e2723;">{rec.type_label}</span>
                                <span class="badge {conf_badge_class}">Evidence: {rec.confidence}</span>
                            </div>
                            <div class="rec-recovery-highlight">
                                Potential Recovery: {rec.estimated_recovery_label}
                            </div>
                        </div>
                        <div class="rec-title">{rec.title}</div>
                        <div style="font-size:0.82rem;color:var(--muted);margin-bottom:0.6rem;">
                            Target: <code>{rec.target_name}</code> · Category: <strong>{rec.category}</strong> · Total Size: <strong>{rec.size_label}</strong>
                        </div>
                        <div class="rec-block-title">WHY THIS WAS FLAGGED</div>
                        <div style="font-size:0.86rem;color:var(--text);line-height:1.5;">
                            {'<br>'.join('✓ ' + reason for reason in rec.reasons)}
                        </div>
                        <div class="rec-block-title">POTENTIAL IMPACT</div>
                        <div class="rec-impact-box">{rec.impact_description}</div>
                        <div class="rec-block-title">SUGGESTED ACTION</div>
                        <div class="rec-action-box">👉 {rec.suggested_action}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                # Action buttons & expandable inspection
                col_exp1, col_exp2 = st.columns((2, 1))
                with col_exp1:
                    with st.expander(f"🔍 Inspect File Details: {rec.target_name} ({rec.id})", expanded=False):
                        col_d1, col_d2 = st.columns(2)
                        with col_d1:
                            st.markdown(f"**Primary Path:** `{rec.target_path}`")
                            st.markdown(f"**Category:** {rec.category}")
                            st.markdown(f"**Size:** {rec.size_label} ({rec.size_bytes:,} bytes)")
                            st.markdown(f"**Last Modified:** {rec.modified_at}")
                            if rec.age_days is not None:
                                st.markdown(f"**Age:** {rec.age_days:,} days")
                        with col_d2:
                            st.markdown(f"**Estimated Recovery:** {rec.estimated_recovery_label}")
                            st.markdown(f"**Evidence Confidence:** {rec.confidence}")
                            st.markdown(f"**Review Priority Score:** {rec.score_weight:.1f}")
                            st.markdown(f"**Signals:** `{', '.join(rec.signals)}`")

                        if len(rec.all_paths) > 1:
                            st.markdown(f"**All {len(rec.all_paths)} Duplicate Copy Locations:**")
                            for p in rec.all_paths:
                                st.text(f"• {p}")

                with col_exp2:
                    explain_clicked = st.button(
                        f"💡 Explain with Qwen",
                        key=f"btn_explain_{rec.id}",
                        help="Generate an on-demand AI explanation from TCET CoE Qwen for this specific recommendation.",
                    )

                if explain_clicked:
                    with st.spinner("Requesting explanation from TCET CoE Qwen…"):
                        expl_stream = qwen_service.explain_recommendation_stream(rec)
                        expl_text = st.write_stream(expl_stream)
                        st.session_state.qwen_rec_explanations[rec.id] = expl_text

                elif rec.id in st.session_state.qwen_rec_explanations:
                    st.info(f"🤖 **Qwen AI Explanation:**\n\n{st.session_state.qwen_rec_explanations[rec.id]}")

    # -----------------------------------------------------------------------
    # TAB 3: Storage Distribution
    # -----------------------------------------------------------------------
    with tab_dist:
        st.subheader("Storage Distribution by Category")
        st.caption("Breakdown of scanned storage and file counts across detected categories.")

        dist_data = [
            {
                "Category": cd.category,
                "Files": cd.file_count,
                "% Files": f"{cd.files_pct:.1f}%",
                "Storage": cd.total_size_label,
                "% Storage": f"{cd.storage_pct:.1f}%",
                "Total Bytes": cd.total_bytes,
            }
            for cd in cat_distribution
        ]
        dist_df = pd.DataFrame(dist_data)

        col_t, col_c = st.columns((3, 2), gap="large")
        with col_t:
            st.dataframe(
                dist_df[["Category", "Files", "% Files", "Storage", "% Storage"]],
                use_container_width=True,
                hide_index=True,
            )
        with col_c:
            if not dist_df.empty:
                chart_df = pd.DataFrame(
                    {
                        "Category": [cd.category for cd in cat_distribution],
                        "Storage (MB)": [round(cd.total_bytes / (1024 * 1024), 2) for cd in cat_distribution],
                    }
                ).set_index("Category")
                st.bar_chart(chart_df, height=280)

    # -----------------------------------------------------------------------
    # TAB 4: Large Files
    # -----------------------------------------------------------------------
    with tab_large:
        st.subheader(f"Large Files (≥ {large_threshold_mb} MB)")
        st.caption(
            f"Found {large_report.count:,} files exceeding {large_threshold_mb} MB, "
            f"consuming {large_report.total_size_label} in total. Sorted largest first."
        )

        if not large_report.files:
            st.success(f"No files found exceeding {large_threshold_mb} MB.")
        else:
            large_df = pd.DataFrame(
                [
                    {
                        "Name": lf.name,
                        "Category": lf.category,
                        "Ext": lf.extension,
                        "Size": lf.size_label,
                        "Modified": lf.modified_at,
                        "Path": lf.path,
                        "Size Bytes": lf.size_bytes,
                    }
                    for lf in large_report.files
                ]
            )

            search_lf = st.text_input("Filter large files", placeholder="Search name or path…", key="search_lf")
            if search_lf.strip():
                q = search_lf.strip().lower()
                large_df = large_df[
                    large_df["Name"].str.lower().str.contains(q, na=False)
                    | large_df["Path"].str.lower().str.contains(q, na=False)
                ]

            st.dataframe(
                large_df[["Name", "Category", "Ext", "Size", "Modified", "Path"]],
                use_container_width=True,
                hide_index=True,
                height=380,
            )

    # -----------------------------------------------------------------------
    # TAB 5: Potentially Stale Files
    # -----------------------------------------------------------------------
    with tab_stale:
        st.subheader(f"Potentially Stale Files (Older than {stale_days_threshold} days)")
        st.caption(
            f"Found {stale_report.count:,} files modified more than {stale_days_threshold} days ago "
            f"({stale_report.total_size_label}). Labeled neutrally as review candidates; age alone does not prove a file is useless."
        )

        if not stale_report.files:
            st.success(f"No files found older than {stale_days_threshold} days.")
        else:
            stale_df = pd.DataFrame(
                [
                    {
                        "Name": sf.name,
                        "Category": sf.category,
                        "Size": sf.size_label,
                        "Age (Days)": sf.age_days,
                        "Last Modified": sf.modified_at,
                        "Path": sf.path,
                    }
                    for sf in stale_report.files
                ]
            )

            search_stale = st.text_input("Filter stale files", placeholder="Search name or path…", key="search_stale")
            if search_stale.strip():
                q = search_stale.strip().lower()
                stale_df = stale_df[
                    stale_df["Name"].str.lower().str.contains(q, na=False)
                    | stale_df["Path"].str.lower().str.contains(q, na=False)
                ]

            st.dataframe(
                stale_df[["Name", "Category", "Size", "Age (Days)", "Last Modified", "Path"]],
                use_container_width=True,
                hide_index=True,
                height=380,
            )

    # -----------------------------------------------------------------------
    # TAB 6: Potential Temporary / Cache Files
    # -----------------------------------------------------------------------
    with tab_temp:
        st.subheader("Potential Temporary / Cache Files")
        st.caption(
            "Heuristic detection identifying files matching temp extensions (.tmp, .bak, .log), "
            "lock patterns (~$), or cache directory names. These are heuristic indicators for review, not guaranteed waste."
        )

        if not temp_report.files:
            st.success("No potential temporary or cache-like files detected.")
        else:
            st.write(f"**Found:** {temp_report.count:,} candidate files · **Total:** {temp_report.total_size_label}")
            temp_df = pd.DataFrame(
                [
                    {
                        "Name": tf.name,
                        "Category": tf.category,
                        "Size": tf.size_label,
                        "Detection Reason": tf.reason,
                        "Modified": tf.modified_at,
                        "Path": tf.path,
                    }
                    for tf in temp_report.files
                ]
            )

            search_temp = st.text_input("Filter temp/cache candidates", placeholder="Search name, path, or reason…", key="search_temp")
            if search_temp.strip():
                q = search_temp.strip().lower()
                temp_df = temp_df[
                    temp_df["Name"].str.lower().str.contains(q, na=False)
                    | temp_df["Path"].str.lower().str.contains(q, na=False)
                    | temp_df["Detection Reason"].str.lower().str.contains(q, na=False)
                ]

            st.dataframe(
                temp_df[["Name", "Category", "Size", "Detection Reason", "Modified", "Path"]],
                use_container_width=True,
                hide_index=True,
                height=380,
            )

    # -----------------------------------------------------------------------
    # TAB 7: Exact Duplicate Waste (Phase 2 Integration)
    # -----------------------------------------------------------------------
    with tab_dup:
        st.subheader("Exact Duplicate Detection (SHA-256)")
        st.caption(
            "Exact duplicates are files with identical SHA-256 hashes (byte-for-byte identical). "
            "Finding duplicates streams candidate files in 1 MiB chunks. Nothing is modified."
        )

        if st.button("Find exact duplicates", type="primary", key="find_duplicates_btn"):
            bar = st.progress(0.0, text="Preparing candidate files …")
            last_update = [0.0]

            def on_progress(done: int, total: int) -> None:
                now = time.monotonic()
                if done == total or now - last_update[0] >= 0.1:
                    last_update[0] = now
                    bar.progress(done / total, text=f"Hashed {done:,} of {total:,} candidate files")

            st.session_state.duplicates = find_duplicates(records, progress=on_progress)
            bar.empty()
            st.rerun()

        report = st.session_state.duplicates
        if report is None:
            st.info("Click **Find exact duplicates** to scan candidate files for byte-level duplicates.")
        else:
            st.markdown(
                f"""
                <div class="metric-grid">
                    {metric_card("Duplicate groups", f"{report.group_count:,}", "Sets of identical files")}
                    {metric_card("Duplicate files", f"{report.duplicate_files:,}", f"{report.redundant_files:,} redundant copies")}
                    {metric_card("Redundant storage", report.redundant_size_label, "Waste = size × (copies − 1)")}
                    {metric_card("Files hashed", f"{report.hashed_files:,}", f"of {report.candidate_files:,} candidates · {format_size(report.bytes_hashed)} read")}
                </div>
                """,
                unsafe_allow_html=True,
            )

            if report.errors:
                with st.expander(f"Files skipped during hashing ({len(report.errors)})"):
                    st.write("\n".join(report.errors[:50]))
                    if len(report.errors) > 50:
                        st.caption(f"…and {len(report.errors) - 50} more")

            if not report.groups:
                st.success("No exact duplicates found among the files that could be read.")
            else:
                limit = st.number_input(
                    "Groups to show",
                    min_value=1,
                    max_value=1_000,
                    value=min(25, max(report.group_count, 1)),
                    step=5,
                    key="dup_group_limit",
                )
                shown = report.groups[: int(limit)]
                st.caption(f"Showing {len(shown):,} of {report.group_count:,} groups, largest redundant storage first.")

                for number, group in enumerate(shown, start=1):
                    label = (
                        f"Group {number} · {group.file_count} files · "
                        f"{group.total_size_label} total · {group.redundant_size_label} redundant"
                    )
                    with st.expander(label):
                        st.caption(f"{format_size(group.size_bytes)} per file · SHA-256")
                        st.code(group.sha256, language=None)
                        st.dataframe(
                            pd.DataFrame(
                                {
                                    "Name": [f.name for f in group.files],
                                    "Folder": [f.parent for f in group.files],
                                    "Modified": [f.modified_at for f in group.files],
                                }
                            ),
                            use_container_width=True,
                            hide_index=True,
                        )

    # -----------------------------------------------------------------------
    # TAB 8: Storage Recovery Simulator
    # -----------------------------------------------------------------------
    with tab_sim:
        st.subheader("Storage Recovery Simulator")
        st.caption(
            "Simulate potential storage recovery across different candidate pools without double-counting files. "
            "Differentiates guaranteed byte-for-byte redundant copies from heuristic review candidates."
        )

        st.markdown(
            f"""
            <div class="recovery-grid">
                <div class="recovery-card tier1">
                    <div class="recovery-tier-tag">Tier 1 · Exact Recoverable</div>
                    <h4>Exact Duplicates</h4>
                    <div class="recovery-value">{recovery.tier1_exact_label}</div>
                    <div class="recovery-desc">
                        Recoverable by keeping 1 original per duplicate set. Zero data loss risk.
                        <br><strong>{recovery.exact_recoverable_files:,} redundant copies</strong>
                    </div>
                </div>
                <div class="recovery-card tier2">
                    <div class="recovery-tier-tag">Tier 2 · Duplicates + Temp/Cache</div>
                    <h4>+ Temp & Cache Candidates</h4>
                    <div class="recovery-value">{recovery.tier2_with_temp_label}</div>
                    <div class="recovery-desc">
                        Includes Tier 1 + non-duplicate temporary/cache-like files.
                        <br><strong>+{recovery.temp_cache_candidate_files:,} temp candidate files ({recovery.temp_cache_candidate_label})</strong>
                    </div>
                </div>
                <div class="recovery-card tier3">
                    <div class="recovery-tier-tag">Tier 3 · Full Potential Review Pool</div>
                    <h4>+ Potentially Stale Files</h4>
                    <div class="recovery-value">{recovery.tier3_full_review_label}</div>
                    <div class="recovery-desc">
                        Full candidate review pool (duplicates + temp + files > {stale_days_threshold}d old).
                        <br><strong>+{recovery.stale_candidate_files:,} stale candidate files ({recovery.stale_candidate_label})</strong>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        sim_df = pd.DataFrame(
            [
                {
                    "Recovery Tier": "Tier 1: Exact Duplicate Recovery",
                    "Safety Level": "100% Identical Copies (Keeping 1 copy)",
                    "Files Involved": recovery.exact_recoverable_files,
                    "Estimated Recovery": recovery.tier1_exact_label,
                },
                {
                    "Recovery Tier": "Tier 2: Duplicates + Temp / Cache",
                    "Safety Level": "Review Candidate (Heuristic Temporary)",
                    "Files Involved": recovery.exact_recoverable_files + recovery.temp_cache_candidate_files,
                    "Estimated Recovery": recovery.tier2_with_temp_label,
                },
                {
                    "Recovery Tier": "Tier 3: Full Review Pool (+ Stale)",
                    "Safety Level": "Review Candidate (Age > threshold)",
                    "Files Involved": (
                        recovery.exact_recoverable_files
                        + recovery.temp_cache_candidate_files
                        + recovery.stale_candidate_files
                    ),
                    "Estimated Recovery": recovery.tier3_full_review_label,
                },
            ]
        )
        st.dataframe(sim_df, use_container_width=True, hide_index=True)

        st.info(f"ℹ️ **Safety Note:** {recovery.disclaimer}")

    # -----------------------------------------------------------------------
    # TAB 9: Full Inventory (Phase 1)
    # -----------------------------------------------------------------------
    with tab_inv:
        st.subheader("File Inventory & Filters")
        st.caption("Search, filter, and inspect scanned metadata.")

        frame = records_to_frame(records)
        col_cat, col_search = st.columns((1, 2))
        with col_cat:
            cat_options = ["All"] + sorted(frame["category"].unique().tolist())
            selected_cat = st.selectbox("Category filter", cat_options, key="inv_cat_filter")
        with col_search:
            inv_query = st.text_input("Search inventory", placeholder="invoice, notes, script, .py…", key="inv_search")

        inv_view = frame.copy()
        if selected_cat != "All":
            inv_view = inv_view[inv_view["category"] == selected_cat]
        if inv_query.strip():
            q = inv_query.strip().lower()
            inv_view = inv_view[
                inv_view["name"].str.lower().str.contains(q, na=False)
                | inv_view["path"].str.lower().str.contains(q, na=False)
            ]

        display_inv = inv_view[
            [
                "name",
                "category",
                "extension",
                "size_label",
                "modified_at",
                "created_at",
                "mime_type",
                "parent",
            ]
        ].rename(
            columns={
                "name": "Name",
                "category": "Category",
                "extension": "Ext",
                "size_label": "Size",
                "modified_at": "Modified",
                "created_at": "Created",
                "mime_type": "MIME",
                "parent": "Folder",
            }
        )

        st.caption(f"Showing {len(display_inv):,} of {len(frame):,} files")
        st.dataframe(display_inv, use_container_width=True, hide_index=True, height=400)

    # -----------------------------------------------------------------------
    # Global Skipped / Errors Expander
    # -----------------------------------------------------------------------
    if st.session_state.errors:
        with st.expander(f"Skipped / unreadable files during scan ({len(st.session_state.errors)})"):
            st.write("\n".join(st.session_state.errors[:50]))
            if len(st.session_state.errors) > 50:
                st.caption(f"…and {len(st.session_state.errors) - 50} more")
