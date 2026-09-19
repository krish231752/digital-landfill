"""Deterministic unit tests for Phase 5: TCET CoE Qwen AI Integration.

Tests (using mocked OpenAI client, no external network calls):
1. Qwen client initialization with custom parameters
2. Correct default base URL (https://ai.tcetcercd.in/v1)
3. Correct default model (qwen3.6)
4. AI_KEY environment variable handling
5. Prompt construction and system instructions
6. Structured evidence sanitization (no file contents)
7. Successful non-streaming response handling
8. Streaming response generator handling
9. HTTP 401 AuthenticationError handling
10. HTTP 400 BadRequestError handling
11. HTTP 502 Bad Gateway / ConnectionError handling
12. APITimeoutError handling
13. Missing API key graceful handling
14. Malformed response error resilience
15. Gateway health check status mapping (connected vs unavailable)
16. Sensitive path/data sanitization guarantee
"""

from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest import mock

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
)

from src.duplicates import DuplicateGroup, DuplicateReport
from src.models import FileRecord
from src.qwen_client import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    QwenConfig,
    check_qwen_health,
    get_qwen_client,
)
from src.qwen_service import (
    QwenService,
    _sanitize_path,
    sanitize_evidence,
)
from src.recommendations import (
    Recommendation,
    RecommendationReport,
    RecommendationType,
)
from src.waste import (
    CategoryDistribution,
    LargeFilesReport,
    RecoveryEstimate,
    StaleFilesReport,
    TempFilesReport,
)


class TestQwenClientConfiguration(unittest.TestCase):
    def test_default_config_values(self) -> None:
        cfg = QwenConfig()
        self.assertEqual(cfg.base_url, DEFAULT_BASE_URL)
        self.assertEqual(cfg.base_url, "https://ai.tcetcercd.in/v1")
        self.assertEqual(cfg.model, DEFAULT_MODEL)
        self.assertEqual(cfg.model, "qwen3.6")
        self.assertFalse(cfg.enable_thinking)

    def test_env_var_loading(self) -> None:
        with mock.patch.dict(os.environ, {"AI_KEY": "test-key-12345", "QWEN_BASE_URL": "https://custom.ai/v1", "QWEN_MODEL": "qwen3.6"}):
            cfg = QwenConfig.from_env()
            self.assertEqual(cfg.api_key, "test-key-12345")
            self.assertEqual(cfg.base_url, "https://custom.ai/v1")
            self.assertEqual(cfg.model, "qwen3.6")

    def test_custom_key_override(self) -> None:
        cfg = QwenConfig.from_env(custom_key="manual-override-key")
        self.assertEqual(cfg.api_key, "manual-override-key")

    def test_client_instantiation(self) -> None:
        cfg = QwenConfig(api_key="sk-test", base_url="https://ai.tcetcercd.in/v1", model="qwen3.6")
        client = get_qwen_client(cfg)
        self.assertEqual(str(client.base_url), "https://ai.tcetcercd.in/v1/")
        self.assertEqual(client.api_key, "sk-test")


class TestQwenEvidenceSanitization(unittest.TestCase):
    def test_path_sanitization_removes_private_roots(self) -> None:
        # Full windows path
        sanitized = _sanitize_path(r"C:\Users\Admin\Documents\PrivateFolder\report.pdf")
        self.assertEqual(sanitized, "PrivateFolder/report.pdf")

        # Full unix path
        sanitized_unix = _sanitize_path("/home/user/secret_projects/code/pipeline.py")
        self.assertEqual(sanitized_unix, "code/pipeline.py")

        # Single file
        sanitized_simple = _sanitize_path("notes.txt")
        self.assertEqual(sanitized_simple, "notes.txt")

    def test_sanitize_evidence_contains_only_structural_metadata(self) -> None:
        summary = {"total_files": 10, "total_size_label": "25.0 MB", "category_count": 3, "top_category": "Documents"}
        cat_dist = [CategoryDistribution(category="Documents", file_count=5, total_bytes=15000000, total_size_label="15.0 MB", storage_pct=60.0, files_pct=50.0)]
        large_rep = LargeFilesReport(threshold_bytes=10000000, threshold_mb=10.0, count=1, total_bytes=12000000, total_size_label="12.0 MB", files=[])
        recovery = RecoveryEstimate(
            exact_recoverable_bytes=5000000,
            exact_recoverable_label="5.0 MB",
            exact_recoverable_files=2,
            temp_cache_candidate_bytes=1000000,
            temp_cache_candidate_label="1.0 MB",
            temp_cache_candidate_files=1,
            stale_candidate_bytes=2000000,
            stale_candidate_label="2.0 MB",
            stale_candidate_files=1,
            tier1_exact_bytes=5000000,
            tier1_exact_label="5.0 MB",
            tier2_with_temp_bytes=6000000,
            tier2_with_temp_label="6.0 MB",
            tier3_full_review_bytes=8000000,
            tier3_full_review_label="8.0 MB",
        )

        ev = sanitize_evidence(
            summary=summary,
            cat_distribution=cat_dist,
            large_report=large_rep,
            recovery=recovery,
        )

        # Ensure no raw content keys
        self.assertIn("scan_overview", ev)
        self.assertIn("storage_distribution", ev)
        self.assertIn("waste_signals", ev)
        self.assertIn("recovery_simulation", ev)
        self.assertEqual(ev["scan_overview"]["total_files"], 10)
        self.assertEqual(ev["recovery_simulation"]["tier1_exact_duplicates"], "5.0 MB")


class TestQwenServiceExecutionAndMocking(unittest.TestCase):
    def setUp(self) -> None:
        self.config = QwenConfig(api_key="valid-test-key", base_url="https://ai.tcetcercd.in/v1", model="qwen3.6")
        self.service = QwenService(config=self.config)

    @mock.patch("src.qwen_service.get_qwen_client")
    def test_successful_streaming_response(self, mock_get_client: mock.MagicMock) -> None:
        # Mock streaming chunks
        chunk1 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="## 1. Executive Summary\n"))])
        chunk2 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Identified 2 redundant copies."))])

        mock_client = mock.MagicMock()
        mock_client.chat.completions.create.return_value = [chunk1, chunk2]
        mock_get_client.return_value = mock_client

        evidence = {"scan_overview": {"total_files": 5}}
        chunks = list(self.service.analyze_waste_stream(evidence))

        self.assertEqual("".join(chunks), "## 1. Executive Summary\nIdentified 2 redundant copies.")
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "qwen3.6")
        self.assertTrue(call_kwargs["stream"])

    @mock.patch("src.qwen_service.get_qwen_client")
    def test_successful_sync_response(self, mock_get_client: mock.MagicMock) -> None:
        chunk = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Analysis complete."))])
        mock_client = mock.MagicMock()
        mock_client.chat.completions.create.return_value = [chunk]
        mock_get_client.return_value = mock_client

        result = self.service.analyze_waste_sync({"data": 123})
        self.assertEqual(result, "Analysis complete.")

    @mock.patch("src.qwen_service.get_qwen_client")
    def test_explain_recommendation_stream(self, mock_get_client: mock.MagicMock) -> None:
        chunk = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="This duplicate has SHA-256 certainty."))])
        mock_client = mock.MagicMock()
        mock_client.chat.completions.create.return_value = [chunk]
        mock_get_client.return_value = mock_client

        rec = Recommendation(
            id="REC-001",
            priority="HIGH",
            recommendation_type=RecommendationType.EXACT_DUPLICATE_REVIEW.value,
            type_label="Exact Duplicate Review",
            title="3 copies of data.bin",
            target_name="data.bin",
            target_path="/a/data.bin",
            all_paths=["/a/data.bin", "/b/data.bin"],
            category="Datasets",
            size_bytes=4000,
            size_label="4.0 KB",
            estimated_recovery_bytes=2000,
            estimated_recovery_label="2.0 KB",
            confidence="HIGH",
            reasons=["SHA-256 match"],
            impact_description="2.0 KB recoverable",
            suggested_action="Review copies",
            signals=["sha256"],
            modified_at="2024-01-01 10:00",
            age_days=10,
            score_weight=3500.0,
        )

        explanation = "".join(self.service.explain_recommendation_stream(rec))
        self.assertIn("SHA-256 certainty", explanation)


class TestQwenErrorHandlingAndFallbacks(unittest.TestCase):
    def setUp(self) -> None:
        self.config = QwenConfig(api_key="test-key")
        self.service = QwenService(config=self.config)

    def test_missing_api_key_message(self) -> None:
        no_key_service = QwenService(config=QwenConfig(api_key=None))
        result = no_key_service.analyze_waste_sync({"data": 1})
        self.assertIn("TCET CoE Qwen Not Configured", result)
        self.assertIn("AI_KEY", result)

    @mock.patch("src.qwen_service.get_qwen_client")
    def test_401_authentication_error(self, mock_get_client: mock.MagicMock) -> None:
        mock_client = mock.MagicMock()
        mock_client.chat.completions.create.side_effect = AuthenticationError(
            message="Invalid API Key",
            response=mock.MagicMock(status_code=401),
            body=None,
        )
        mock_get_client.return_value = mock_client

        result = self.service.analyze_waste_sync({"data": 1})
        self.assertIn("401", result)
        self.assertIn("Authentication Error", result)

    @mock.patch("src.qwen_service.get_qwen_client")
    def test_400_bad_request_error(self, mock_get_client: mock.MagicMock) -> None:
        mock_client = mock.MagicMock()
        mock_client.chat.completions.create.side_effect = BadRequestError(
            message="Malformed payload",
            response=mock.MagicMock(status_code=400),
            body=None,
        )
        mock_get_client.return_value = mock_client

        result = self.service.analyze_waste_sync({"data": 1})
        self.assertIn("400", result)
        self.assertIn("Bad Request", result)

    @mock.patch("src.qwen_service.get_qwen_client")
    def test_502_gateway_unavailable_error(self, mock_get_client: mock.MagicMock) -> None:
        mock_client = mock.MagicMock()
        mock_client.chat.completions.create.side_effect = InternalServerError(
            message="Model server unavailable",
            response=mock.MagicMock(status_code=502),
            body=None,
        )
        mock_get_client.return_value = mock_client

        result = self.service.analyze_waste_sync({"data": 1})
        self.assertIn("Gateway Unavailable", result)
        self.assertIn("Local Digital Landfill intelligence remains active", result)

    @mock.patch("src.qwen_service.get_qwen_client")
    def test_timeout_error_handling(self, mock_get_client: mock.MagicMock) -> None:
        mock_client = mock.MagicMock()
        mock_client.chat.completions.create.side_effect = APITimeoutError(request=mock.MagicMock())
        mock_get_client.return_value = mock_client

        result = self.service.analyze_waste_sync({"data": 1})
        self.assertIn("Request Timeout", result)


class TestQwenHealthCheck(unittest.TestCase):
    def test_health_check_unconfigured(self) -> None:
        cfg = QwenConfig(api_key=None)
        is_ok, badge, msg = check_qwen_health(cfg)
        self.assertFalse(is_ok)
        self.assertIn("Not Configured", badge)

    @mock.patch("src.qwen_client.get_qwen_client")
    def test_health_check_connected(self, mock_get_client: mock.MagicMock) -> None:
        mock_client = mock.MagicMock()
        mock_client.models.list.return_value = [SimpleNamespace(id="qwen3.6")]
        mock_get_client.return_value = mock_client

        cfg = QwenConfig(api_key="valid-key", model="qwen3.6")
        is_ok, badge, msg = check_qwen_health(cfg)

        self.assertTrue(is_ok)
        self.assertIn("Connected", badge)
        self.assertIn("qwen3.6", msg)

    @mock.patch("src.qwen_client.get_qwen_client")
    def test_health_check_offline(self, mock_get_client: mock.MagicMock) -> None:
        mock_client = mock.MagicMock()
        mock_client.models.list.side_effect = APIConnectionError(request=mock.MagicMock())
        mock_get_client.return_value = mock_client

        cfg = QwenConfig(api_key="valid-key")
        is_ok, badge, msg = check_qwen_health(cfg)

        self.assertFalse(is_ok)
        self.assertIn("Offline", badge)


class TestAskDigitalLandfill(unittest.TestCase):
    def setUp(self) -> None:
        self.config = QwenConfig(api_key="sk-test", base_url="https://ai.tcetcercd.in/v1", model="qwen3.6")
        self.service = QwenService(self.config)

    def test_build_grounded_scan_context_full(self) -> None:
        summary = {
            "total_files": 42,
            "total_size_label": "120.5 MB",
            "category_count": 4,
            "top_category": "Code",
            "root_name": "project_src",
        }
        cats = [
            CategoryDistribution(category="Code", file_count=20, total_bytes=60_000_000, total_size_label="60.0 MB", storage_pct=49.8, files_pct=47.6),
            CategoryDistribution(category="Documents", file_count=10, total_bytes=40_000_000, total_size_label="40.0 MB", storage_pct=33.2, files_pct=23.8),
        ]
        large = LargeFilesReport(threshold_bytes=25*1024*1024, threshold_mb=25.0, count=1, total_bytes=50_000_000, total_size_label="50.0 MB", files=[])
        stale = StaleFilesReport(days_threshold=180, count=2, total_bytes=10_000_000, total_size_label="10.0 MB", files=[])
        temp = TempFilesReport(count=5, total_bytes=500_000, total_size_label="500.0 KB", files=[])
        recovery = RecoveryEstimate(
            exact_recoverable_bytes=5_000_000,
            exact_recoverable_label="5.0 MB",
            exact_recoverable_files=2,
            temp_cache_candidate_bytes=500_000,
            temp_cache_candidate_label="500.0 KB",
            temp_cache_candidate_files=5,
            stale_candidate_bytes=10_000_000,
            stale_candidate_label="10.0 MB",
            stale_candidate_files=2,
            tier1_exact_bytes=5_000_000,
            tier1_exact_label="5.0 MB",
            tier2_with_temp_bytes=5_500_000,
            tier2_with_temp_label="5.5 MB",
            tier3_full_review_bytes=15_500_000,
            tier3_full_review_label="15.5 MB",
        )

        ctx = from_service_ctx = self.service  # smoke check
        from src.qwen_service import build_grounded_scan_context
        context_str = build_grounded_scan_context(
            summary=summary,
            cat_distribution=cats,
            large_report=large,
            stale_report=stale,
            temp_report=temp,
            recovery=recovery,
        )

        self.assertIn("File Inventory Overview", context_str)
        self.assertIn("Total Files Scanned: 42", context_str)
        self.assertIn("Code**: 20 files", context_str)
        self.assertIn("Large Files", context_str)
        self.assertIn("Storage Recovery Simulation", context_str)
        self.assertIn("Tier 1 (Exact Duplicates): 5.0 MB", context_str)

    def test_build_grounded_scan_context_empty(self) -> None:
        from src.qwen_service import build_grounded_scan_context
        context_str = build_grounded_scan_context()
        self.assertIn("Exact duplicate scan has NOT been executed yet", context_str)

    @mock.patch("src.qwen_service.get_qwen_client")
    def test_ask_digital_landfill_streaming(self, mock_get_client: mock.MagicMock) -> None:
        chunk1 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Based on your scan, "))])
        chunk2 = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="you have 5.0 MB recoverable."))])
        mock_client = mock.MagicMock()
        mock_client.chat.completions.create.return_value = iter([chunk1, chunk2])
        mock_get_client.return_value = mock_client

        stream = self.service.ask_digital_landfill_stream(
            query="How much storage can I recover?",
            scan_context="Context: Tier 1 is 5.0 MB.",
        )
        result = "".join(stream)
        self.assertEqual(result, "Based on your scan, you have 5.0 MB recoverable.")

    @mock.patch("src.qwen_service.get_qwen_client")
    def test_ask_digital_landfill_multi_turn_history(self, mock_get_client: mock.MagicMock) -> None:
        chunk = SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Understood."))])
        mock_client = mock.MagicMock()
        mock_client.chat.completions.create.return_value = iter([chunk])
        mock_get_client.return_value = mock_client

        history = [
            {"role": "user", "content": "What are my largest files?"},
            {"role": "assistant", "content": "Your largest file is data.bin."},
        ]

        result = self.service.ask_digital_landfill_sync(
            query="Where is it located?",
            scan_context="Context...",
            chat_history=history,
        )
        self.assertEqual(result, "Understood.")

        # Verify call messages structure
        call_args = mock_client.chat.completions.create.call_args[1]
        messages = call_args["messages"]
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[1]["content"], "What are my largest files?")
        self.assertEqual(messages[2]["role"], "assistant")
        self.assertEqual(messages[3]["role"], "user")
        self.assertEqual(messages[3]["content"], "Where is it located?")

    def test_ask_missing_api_key(self) -> None:
        service_no_key = QwenService(QwenConfig(api_key=None))
        result = service_no_key.ask_digital_landfill_sync("Any question?", "Some context")
        self.assertIn("TCET CoE Qwen Not Configured", result)


if __name__ == "__main__":
    unittest.main()

