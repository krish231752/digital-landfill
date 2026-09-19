"""Phase 5 — TCET CoE Qwen AI Service Layer.

Provides structured prompt construction, evidence sanitization, streaming inference,
strategic reasoning mode control, and resilient error handling for the TCET Centre of
Excellence AI Gateway.

Adheres to strict privacy and local-first principles:
- Only sanitized structured evidence is sent to Qwen.
- Full file contents are NEVER read or uploaded.
- Digital Landfill remains 100% functional even if the AI gateway is offline.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Generator, Sequence

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
)

from src.duplicates import DuplicateReport
from src.models import FileRecord, format_size
from src.qwen_client import QwenConfig, get_qwen_client
from src.recommendations import Recommendation, RecommendationReport
from src.waste import (
    CategoryDistribution,
    LargeFilesReport,
    RecoveryEstimate,
    StaleFilesReport,
    TempFilesReport,
)

SYSTEM_PROMPT = """You are the AI Waste Intelligence and Reasoning layer for DIGITAL LANDFILL, powered by the TCET Centre of Excellence AI Gateway (Qwen3.6-35B-A3B).

Your responsibility is to analyze verified, structured digital waste signals and explain storage patterns to the user in a clear, explainable, and actionable manner.

Strict Operational Guidelines:
1. ONLY utilize the supplied structured evidence. Never invent filesystem facts or hallucinate files/groups.
2. NEVER declare that any file is "guaranteed safe to delete". Frame all items as "review candidates" for human-in-the-loop decision making.
3. Clearly distinguish verified empirical facts (exact SHA-256 byte-for-byte duplicates) from heuristic indicators (stale modification ages, temporary file naming patterns).
4. Always recommend manual human review before any cleanup action.
5. Format your output in clean, structured Markdown with the following exact sections:
   - ## 1. Executive Summary
   - ## 2. Key Findings
   - ## 3. Waste Analysis
   - ## 4. Review Recommendations
   - ## 5. Potential Storage Recovery
   - ## 6. Important Limitations
6. Keep your explanations concise, professional, and directly relevant.
"""

RECOMMENDATION_EXPLAIN_SYSTEM_PROMPT = """You are the explainability assistant for DIGITAL LANDFILL, powered by the TCET Centre of Excellence AI Gateway.

Your task is to explain a specific file/duplicate review recommendation based strictly on the provided structured evidence.

Guidelines:
1. Explain WHY this recommendation matters and the technical rationale behind its priority and evidence confidence.
2. Explain what the evidence proves (e.g. SHA-256 byte-for-byte equality vs heuristic pattern match).
3. Outline a safe, human-in-the-loop review workflow.
4. Keep the explanation concise, structured, and free of hallucinations.
"""

ASK_DIGITAL_LANDFILL_SYSTEM_PROMPT = """You are the interactive "Ask Digital Landfill" AI Assistant, powered by the TCET Centre of Excellence campus AI Gateway (Qwen3.6-35B-A3B).

Your goal is to answer questions about the user's scanned directory, files, storage distribution, duplicate redundancies, waste patterns, and cleanup recommendations based STRICTLY on the provided Grounded Scan Context.

Grounding & Safety Rules:
1. STRICT GROUNDING: Answer questions ONLY using facts and figures found in the Grounded Scan Context. Never invent files, directories, duplicate groups, numbers, or hashes.
2. MISSING DATA: If the user asks about something that was not scanned or is absent from the context (e.g. if exact duplicates have not been computed yet), clearly inform them and suggest running the corresponding scan step.
3. HUMAN-IN-THE-LOOP ADVISORY: Frame all findings as review candidates. Never claim a file is automatically deletable without human review. You cannot delete, move, or modify files.
4. CERTAINTY DISTINCTION: Differentiate between 100% verified facts (e.g. SHA-256 exact byte-for-byte duplicates) and heuristic indicators (e.g. stale age, .tmp naming patterns).
5. FORMATTING: Be concise, clear, and structured. Use bullet points, bold text, or markdown tables when summarizing files or categories.
"""


def _sanitize_path(path_str: str) -> str:
    """Anonymize absolute system paths to relative names or folder/file structures."""
    try:
        p = Path(path_str)
        # Keep parent folder name + file name (e.g., 'documents/report.pdf')
        if len(p.parts) >= 2:
            return f"{p.parts[-2]}/{p.parts[-1]}"
        return p.name
    except Exception:
        return "file"


def sanitize_evidence(
    summary: dict[str, Any] | None = None,
    cat_distribution: list[CategoryDistribution] | None = None,
    duplicate_report: DuplicateReport | None = None,
    large_report: LargeFilesReport | None = None,
    stale_report: StaleFilesReport | None = None,
    temp_report: TempFilesReport | None = None,
    rec_report: RecommendationReport | None = None,
    recovery: RecoveryEstimate | None = None,
) -> dict[str, Any]:
    """Compile structured signals into a compact, privacy-preserving JSON payload.

    No file contents or sensitive absolute user paths are included.
    """
    evidence: dict[str, Any] = {}

    # Scan Overview
    if summary:
        evidence["scan_overview"] = {
            "total_files": summary.get("total_files", 0),
            "total_storage": summary.get("total_size_label", "0 B"),
            "category_count": summary.get("category_count", 0),
            "top_category": summary.get("top_category", "—"),
        }

    # Category Distribution
    if cat_distribution:
        evidence["storage_distribution"] = [
            {
                "category": cd.category,
                "file_count": cd.file_count,
                "storage": cd.total_size_label,
                "storage_percentage": f"{cd.storage_pct}%",
            }
            for cd in cat_distribution[:6]
        ]

    # Duplicate Signals (Phase 2)
    if duplicate_report and duplicate_report.groups:
        evidence["exact_duplicates"] = {
            "group_count": duplicate_report.group_count,
            "total_duplicate_files": duplicate_report.duplicate_files,
            "redundant_copies": duplicate_report.redundant_files,
            "redundant_storage": duplicate_report.redundant_size_label,
            "top_groups": [
                {
                    "file_name": g.files[0].name,
                    "copies": g.file_count,
                    "redundant_storage": g.redundant_size_label,
                    "sha256_prefix": g.sha256[:12] + "...",
                }
                for g in duplicate_report.groups[:5]
            ],
        }
    else:
        evidence["exact_duplicates"] = {"status": "No exact duplicates detected or scan not run"}

    # Waste Intelligence Signals (Phase 3)
    waste_signals: dict[str, Any] = {}
    if large_report:
        waste_signals["large_files"] = {
            "count": large_report.count,
            "total_storage": large_report.total_size_label,
            "threshold_mb": large_report.threshold_mb,
        }
    if stale_report:
        waste_signals["potentially_stale_files"] = {
            "count": stale_report.count,
            "total_storage": stale_report.total_size_label,
            "threshold_days": stale_report.days_threshold,
        }
    if temp_report:
        waste_signals["temp_cache_candidates"] = {
            "count": temp_report.count,
            "total_storage": temp_report.total_size_label,
        }
    evidence["waste_signals"] = waste_signals

    # Storage Recovery Simulation
    if recovery:
        evidence["recovery_simulation"] = {
            "tier1_exact_duplicates": recovery.tier1_exact_label,
            "tier2_with_temp_cache": recovery.tier2_with_temp_label,
            "tier3_full_review_pool": recovery.tier3_full_review_label,
        }

    # Top Recommendations (Phase 4)
    if rec_report and rec_report.recommendations:
        evidence["recommendations_summary"] = {
            "total": rec_report.total_count,
            "high_priority": rec_report.high_count,
            "medium_priority": rec_report.medium_count,
            "low_priority": rec_report.low_count,
            "top_items": [
                {
                    "id": r.id,
                    "priority": r.priority,
                    "type": r.type_label,
                    "target": r.target_name,
                    "category": r.category,
                    "size": r.size_label,
                    "potential_recovery": r.estimated_recovery_label,
                    "confidence": r.confidence,
                    "reasons": r.reasons,
                }
                for r in rec_report.recommendations[:8]
            ],
        }

    return evidence


def build_grounded_scan_context(
    summary: dict[str, Any] | None = None,
    cat_distribution: list[CategoryDistribution] | None = None,
    duplicate_report: DuplicateReport | None = None,
    large_report: LargeFilesReport | None = None,
    stale_report: StaleFilesReport | None = None,
    temp_report: TempFilesReport | None = None,
    rec_report: RecommendationReport | None = None,
    recovery: RecoveryEstimate | None = None,
) -> str:
    """Build a comprehensive, token-efficient, sanitized Markdown context representation.

    Contains structured facts from Phase 1, Phase 2, Phase 3, and Phase 4.
    Strictly excludes full file contents and private root filesystem paths.
    """
    sections: list[str] = []

    # 1. Overview (Phase 1)
    if summary:
        overview_lines = [
            "### 1. File Inventory Overview (Phase 1)",
            f"- Total Files Scanned: {summary.get('total_files', 0):,}",
            f"- Total Storage Footprint: {summary.get('total_size_label', '0 B')}",
            f"- Distinct Categories: {summary.get('category_count', 0)}",
            f"- Top Category: {summary.get('top_category', '—')}",
        ]
        sections.append("\n".join(overview_lines))

    # 2. Storage Distribution (Phase 3)
    if cat_distribution:
        dist_lines = ["### 2. Category Storage Distribution (Phase 3)"]
        for cd in cat_distribution:
            dist_lines.append(
                f"- **{cd.category}**: {cd.file_count:,} files, {cd.total_size_label} ({cd.storage_pct}%)"
            )
        sections.append("\n".join(dist_lines))

    # 3. Exact Duplicate Intelligence (Phase 2)
    if duplicate_report is not None:
        dup_lines = [
            "### 3. Exact Duplicate Intelligence (Phase 2 - SHA-256 Byte-Identical)",
            f"- Total Duplicate Groups: {duplicate_report.group_count:,}",
            f"- Total Duplicate Files: {duplicate_report.duplicate_files:,}",
            f"- Redundant Files (recoverable by keeping 1 copy): {duplicate_report.redundant_files:,}",
            f"- Redundant Storage Footprint: {duplicate_report.redundant_size_label}",
        ]
        if duplicate_report.groups:
            dup_lines.append("Top Duplicate Groups:")
            for idx, g in enumerate(duplicate_report.groups[:6], 1):
                dup_lines.append(
                    f"  {idx}. `{g.files[0].name}`: {g.file_count} copies, "
                    f"size per file: {format_size(g.size_bytes)}, recoverable: {g.redundant_size_label} "
                    f"(Locations: {', '.join(_sanitize_path(f.path) for f in g.files)})"
                )
        sections.append("\n".join(dup_lines))
    else:
        sections.append("### 3. Exact Duplicate Intelligence (Phase 2)\n- Status: Exact duplicate scan has NOT been executed yet.")

    # 4. Waste Intelligence Signals (Phase 3)
    waste_lines = ["### 4. Waste Signals (Phase 3)"]
    if large_report:
        waste_lines.append(
            f"- **Large Files (≥ {large_report.threshold_mb} MB)**: {large_report.count:,} files ({large_report.total_size_label})"
        )
        if large_report.files:
            for f in large_report.files[:5]:
                waste_lines.append(f"  • `{f.name}` ({f.size_label}, category: {f.category})")
    if stale_report:
        waste_lines.append(
            f"- **Potentially Stale Files (> {stale_report.days_threshold} days old)**: {stale_report.count:,} files ({stale_report.total_size_label})"
        )
        if stale_report.files:
            for f in stale_report.files[:5]:
                waste_lines.append(f"  • `{f.name}` ({f.size_label}, last modified: {f.modified_at})")
    if temp_report:
        waste_lines.append(
            f"- **Temporary / Cache Candidates**: {temp_report.count:,} files ({temp_report.total_size_label})"
        )
        if temp_report.files:
            for f in temp_report.files[:5]:
                waste_lines.append(f"  • `{f.name}` ({f.size_label}, heuristic match)")
    sections.append("\n".join(waste_lines))

    # 5. Recovery Simulator (Phase 3)
    if recovery:
        recov_lines = [
            "### 5. Storage Recovery Simulation (Phase 3)",
            f"- Tier 1 (Exact Duplicates): {recovery.tier1_exact_label} ({recovery.exact_recoverable_files:,} redundant copies)",
            f"- Tier 2 (Duplicates + Temp/Cache): {recovery.tier2_with_temp_label} (+{recovery.temp_cache_candidate_files:,} temp files)",
            f"- Tier 3 (Full Potential Review Pool): {recovery.tier3_full_review_label} (+{recovery.stale_candidate_files:,} stale files)",
        ]
        sections.append("\n".join(recov_lines))

    # 6. Structured Recommendations (Phase 4)
    if rec_report and rec_report.recommendations:
        rec_lines = [
            f"### 6. AI Waste Recommendations (Phase 4 - Total: {rec_report.total_count})",
            f"- High Priority: {rec_report.high_count}, Medium: {rec_report.medium_count}, Low: {rec_report.low_count}",
            "Top Ranked Recommendations:",
        ]
        for r in rec_report.recommendations[:8]:
            rec_lines.append(
                f"- **[{r.priority} Priority / {r.confidence} Confidence] {r.title}** ({r.id}):\n"
                f"  • Target: `{r.target_name}` ({r.size_label})\n"
                f"  • Estimated Recovery: {r.estimated_recovery_label}\n"
                f"  • Reasons: {'; '.join(r.reasons)}\n"
                f"  • Suggested Action: {r.suggested_action}"
            )
        sections.append("\n".join(rec_lines))

    return "\n\n".join(sections)


class QwenService:
    """Service abstraction for Qwen AI reasoning on top of Digital Landfill."""

    def __init__(self, config: QwenConfig | None = None) -> None:
        self.config = config or QwenConfig.from_env()

    def analyze_waste_stream(
        self,
        sanitized_evidence: dict[str, Any],
        enable_thinking: bool | None = None,
    ) -> Generator[str, None, None]:
        """Stream comprehensive waste analysis from TCET CoE Qwen."""
        if not self.config.api_key:
            yield (
                "⚠️ **TCET CoE Qwen Not Configured**: AI_KEY is missing. "
                "Please configure `AI_KEY` in your `.env` file or sidebar to enable Qwen reasoning."
            )
            return

        thinking_enabled = (
            self.config.enable_thinking if enable_thinking is None else enable_thinking
        )

        evidence_json = json.dumps(sanitized_evidence, indent=2)
        user_prompt = (
            f"Here is the verified structured evidence from the Digital Landfill scan:\n\n"
            f"```json\n{evidence_json}\n```\n\n"
            f"Please provide a structured AI waste analysis following your operational guidelines."
        )

        try:
            client = get_qwen_client(self.config)
            extra_body = {
                "chat_template_kwargs": {
                    "enable_thinking": thinking_enabled,
                    "reasoning_effort": self.config.reasoning_effort,
                }
            }

            stream = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
                extra_body=extra_body,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except AuthenticationError:
            yield (
                "🔴 **Authentication Error (401)**: The provided `AI_KEY` is invalid or expired. "
                "Please verify your credentials for the TCET CoE AI Gateway."
            )
        except APITimeoutError:
            yield (
                "🔴 **Request Timeout**: The TCET CoE AI Gateway timed out. "
                "The campus model server may be experiencing high demand. Please try again in a moment."
            )
        except (APIConnectionError, InternalServerError):
            yield (
                "🔴 **Gateway Unavailable (502 / Offline)**: Unable to connect to the TCET CoE AI Gateway "
                f"at `{self.config.base_url}`. Campus server may be busy. Local Digital Landfill intelligence remains active."
            )
        except BadRequestError as exc:
            yield f"🔴 **Bad Request (400)**: Malformed request to TCET CoE Gateway ({exc.message if hasattr(exc, 'message') else exc})."
        except Exception as exc:
            yield f"🔴 **AI Gateway Error**: {type(exc).__name__} ({exc}). Local intelligence remains active."

    def analyze_waste_sync(
        self,
        sanitized_evidence: dict[str, Any],
        enable_thinking: bool | None = None,
    ) -> str:
        """Synchronous wrapper for waste analysis."""
        return "".join(self.analyze_waste_stream(sanitized_evidence, enable_thinking=enable_thinking))

    def explain_recommendation_stream(
        self,
        recommendation: Recommendation,
        enable_thinking: bool = False,
    ) -> Generator[str, None, None]:
        """Stream an on-demand contextual explanation for a single recommendation."""
        if not self.config.api_key:
            yield (
                "⚠️ **TCET CoE Qwen Not Configured**: AI_KEY is missing. "
                "Set `AI_KEY` in `.env` to enable on-demand recommendation explanations."
            )
            return

        rec_evidence = {
            "id": recommendation.id,
            "title": recommendation.title,
            "type": recommendation.type_label,
            "priority": recommendation.priority,
            "confidence": recommendation.confidence,
            "target_file": recommendation.target_name,
            "category": recommendation.category,
            "size": recommendation.size_label,
            "estimated_recovery": recommendation.estimated_recovery_label,
            "all_copies_count": len(recommendation.all_paths),
            "reasons": recommendation.reasons,
            "impact": recommendation.impact_description,
            "suggested_action": recommendation.suggested_action,
        }

        user_prompt = (
            f"Explain the technical rationale, evidence confidence, and safe review workflow "
            f"for this specific Digital Landfill recommendation:\n\n"
            f"```json\n{json.dumps(rec_evidence, indent=2)}\n```"
        )

        try:
            client = get_qwen_client(self.config)
            extra_body = {
                "chat_template_kwargs": {
                    "enable_thinking": enable_thinking,
                    "reasoning_effort": "low",
                }
            }

            stream = client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": RECOMMENDATION_EXPLAIN_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                stream=True,
                extra_body=extra_body,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except AuthenticationError:
            yield "🔴 **Authentication Error (401)**: Invalid AI_KEY."
        except APITimeoutError:
            yield "🔴 **Timeout**: Gateway request timed out."
        except (APIConnectionError, InternalServerError):
            yield "🔴 **Gateway Offline (502)**: TCET CoE Gateway is currently unreachable."
        except Exception as exc:
            yield f"🔴 **Error**: {type(exc).__name__} ({exc})."

    def explain_recommendation_sync(
        self,
        recommendation: Recommendation,
        enable_thinking: bool = False,
    ) -> str:
        """Synchronous wrapper for recommendation explanation."""
        return "".join(self.explain_recommendation_stream(recommendation, enable_thinking=enable_thinking))

    def ask_digital_landfill_stream(
        self,
        query: str,
        scan_context: str,
        chat_history: list[dict[str, str]] | None = None,
        enable_thinking: bool | None = None,
    ) -> Generator[str, None, None]:
        """Stream an interactive, grounded answer from TCET CoE Qwen."""
        if not self.config.api_key:
            yield (
                "⚠️ **TCET CoE Qwen Not Configured**: AI_KEY is missing. "
                "Please configure `AI_KEY` in your `.env` / `ai.env` file or sidebar to ask questions."
            )
            return

        thinking_enabled = (
            self.config.enable_thinking if enable_thinking is None else enable_thinking
        )

        system_message = (
            f"{ASK_DIGITAL_LANDFILL_SYSTEM_PROMPT}\n\n"
            f"### Verified Grounded Scan Context:\n"
            f"{scan_context}"
        )

        messages: list[dict[str, str]] = [{"role": "system", "content": system_message}]

        # Append previous conversational turns (up to last 8 messages)
        if chat_history:
            for msg in chat_history[-8:]:
                if msg.get("role") in ("user", "assistant") and msg.get("content"):
                    messages.append({"role": msg["role"], "content": msg["content"]})

        # Append current user query
        messages.append({"role": "user", "content": query})

        try:
            client = get_qwen_client(self.config)
            extra_body = {
                "chat_template_kwargs": {
                    "enable_thinking": thinking_enabled,
                    "reasoning_effort": self.config.reasoning_effort,
                }
            }

            stream = client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                stream=True,
                extra_body=extra_body,
            )

            for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except AuthenticationError:
            yield (
                "🔴 **Authentication Error (401)**: The provided `AI_KEY` is invalid or expired. "
                "Please verify your credentials for the TCET CoE AI Gateway."
            )
        except APITimeoutError:
            yield (
                "🔴 **Request Timeout**: The TCET CoE AI Gateway timed out. "
                "The campus model server may be experiencing high demand. Please try again."
            )
        except (APIConnectionError, InternalServerError):
            yield (
                "🔴 **Gateway Unavailable (502 / Offline)**: Unable to connect to the TCET CoE AI Gateway "
                f"at `{self.config.base_url}`. Campus server may be busy."
            )
        except BadRequestError as exc:
            yield f"🔴 **Bad Request (400)**: {exc.message if hasattr(exc, 'message') else exc}."
        except Exception as exc:
            yield f"🔴 **AI Gateway Error**: {type(exc).__name__} ({exc})."

    def ask_digital_landfill_sync(
        self,
        query: str,
        scan_context: str,
        chat_history: list[dict[str, str]] | None = None,
        enable_thinking: bool | None = None,
    ) -> str:
        """Synchronous wrapper for Ask Digital Landfill."""
        return "".join(
            self.ask_digital_landfill_stream(
                query=query,
                scan_context=scan_context,
                chat_history=chat_history,
                enable_thinking=enable_thinking,
            )
        )

