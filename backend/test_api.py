"""
Unit tests for FastAPI backend routes, security guarantees, and deployment modes.
Verifies:
1. Health check & configuration
2. Scanning integration
3. Grounded Qwen asking
4. Strict deletion constraints
5. Demo / Cloud Mode security restrictions:
   - Arbitrary server paths rejected in demo mode
   - Bundled demo dataset permitted
6. Sub-resource analytical endpoints (/api/files, /api/waste, /api/duplicates, /api/recommendations)
"""

import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from backend.api import app, state, IS_DEMO_MODE


class TestBackendAPI(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.test_dir = tempfile.TemporaryDirectory()
        self.sample_file1 = os.path.join(self.test_dir.name, "sample1.txt")
        self.sample_file2 = os.path.join(self.test_dir.name, "sample2.txt")
        
        with open(self.sample_file1, "w", encoding="utf-8") as f:
            f.write("Hello Digital Landfill World! Duplicate content testing.")
        with open(self.sample_file2, "w", encoding="utf-8") as f:
            f.write("Hello Digital Landfill World! Duplicate content testing.")

    def tearDown(self):
        self.test_dir.cleanup()

    @patch("backend.api.check_qwen_health")
    def test_health_endpoint(self, mock_health):
        mock_health.return_value = (True, "Connected", "TCET CoE Qwen Gateway active")
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("deployment_mode", data)
        self.assertIn("qwen_gateway", data)
        self.assertIn("has_active_scan", data)

    def test_scan_and_summary_endpoints(self):
        scan_resp = self.client.post("/api/scan", json={"root_path": self.test_dir.name})
        self.assertEqual(scan_resp.status_code, 200)
        scan_data = scan_resp.json()
        self.assertEqual(scan_data["status"], "success")
        self.assertEqual(scan_data["data"]["totalFiles"], 2)
        self.assertIn("signals", scan_data["data"])
        self.assertIn("duplicateGroups", scan_data["data"])

        # Test summary endpoint
        summary_resp = self.client.get("/api/summary")
        self.assertEqual(summary_resp.status_code, 200)
        summary_data = summary_resp.json()
        self.assertEqual(summary_data["total_files"], 2)
        self.assertIn("root_name", summary_data)

    def test_analytical_sub_endpoints(self):
        # Scan test directory
        self.client.post("/api/scan", json={"root_path": self.test_dir.name})

        # Test /api/files
        files_resp = self.client.get("/api/files")
        self.assertEqual(files_resp.status_code, 200)
        files_data = files_resp.json()
        self.assertEqual(files_data["total"], 2)
        self.assertEqual(len(files_data["files"]), 2)

        # Test /api/duplicates
        dup_resp = self.client.get("/api/duplicates")
        self.assertEqual(dup_resp.status_code, 200)
        dup_data = dup_resp.json()
        self.assertEqual(dup_data["group_count"], 1)

        # Test /api/waste
        waste_resp = self.client.get("/api/waste")
        self.assertEqual(waste_resp.status_code, 200)
        waste_data = waste_resp.json()
        self.assertIn("waste_score", waste_data)
        self.assertIn("recovery_simulator", waste_data)

        # Test /api/recommendations
        rec_resp = self.client.get("/api/recommendations")
        self.assertEqual(rec_resp.status_code, 200)
        rec_data = rec_resp.json()
        self.assertIn("recommendations", rec_data)

    def test_delete_security_rejected_if_not_confirmed(self):
        # Scan first
        self.client.post("/api/scan", json={"root_path": self.test_dir.name})
        
        # Attempt delete without explicit confirmation
        resp = self.client.post(
            "/api/delete",
            json={
                "path": self.sample_file2,
                "expected_size": os.path.getsize(self.sample_file2),
                "confirmed": False
            }
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("confirmation", resp.json()["detail"].lower())
        self.assertTrue(os.path.exists(self.sample_file2))

    def test_delete_security_rejected_outside_scanned_root(self):
        # Scan test_dir
        self.client.post("/api/scan", json={"root_path": self.test_dir.name})

        # Create another file outside the scanned root
        with tempfile.NamedTemporaryFile(delete=False) as outside_file:
            outside_path = outside_file.name

        try:
            resp = self.client.post(
                "/api/delete",
                json={
                    "path": outside_path,
                    "expected_size": os.path.getsize(outside_path),
                    "confirmed": True
                }
            )
            self.assertEqual(resp.status_code, 403)
            self.assertIn("outside", resp.json()["detail"].lower())
            self.assertTrue(os.path.exists(outside_path))
        finally:
            if os.path.exists(outside_path):
                os.remove(outside_path)

    def test_delete_successful_for_active_scanned_file(self):
        # Scan test_dir
        self.client.post("/api/scan", json={"root_path": self.test_dir.name})
        self.assertTrue(os.path.exists(self.sample_file2))

        # Perform valid deletion
        resp = self.client.post(
            "/api/delete",
            json={
                "path": self.sample_file2,
                "expected_size": os.path.getsize(self.sample_file2),
                "confirmed": True
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertFalse(os.path.exists(self.sample_file2))
        # Total files in active scan recomputed to 1
        self.assertEqual(data["data"]["totalFiles"], 1)

    @patch("backend.api._get_qwen_service")
    def test_ask_qwen_grounded_validation(self, mock_service_fn):
        mock_svc = MagicMock()
        mock_svc.config.model = "qwen3.6"
        mock_svc.ask_digital_landfill_sync.return_value = "There is 1 duplicate group with 2 identical copies."
        mock_service_fn.return_value = mock_svc

        # Scan test_dir
        self.client.post("/api/scan", json={"root_path": self.test_dir.name})
        
        resp = self.client.post(
            "/api/qwen/ask",
            json={
                "query": "How many duplicate files are there?",
                "chat_history": []
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertEqual(data["model"], "qwen3.6")

    @patch("backend.api.IS_DEMO_MODE", True)
    def test_demo_mode_restricts_arbitrary_paths(self):
        # In demo mode, arbitrary paths outside the demo fixtures should be rejected with 403
        resp = self.client.post("/api/scan", json={"root_path": "C:\\Windows\\System32"})
        self.assertEqual(resp.status_code, 403)
        self.assertIn("demo", resp.json()["detail"].lower())

    @patch("backend.api.IS_DEMO_MODE", True)
    def test_demo_mode_allows_test_waste_sample(self):
        # In demo mode, test_waste_sample must be accepted
        if os.path.exists("test_waste_sample"):
            resp = self.client.post("/api/scan", json={"root_path": "test_waste_sample"})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json()["status"], "success")


if __name__ == "__main__":
    unittest.main()
