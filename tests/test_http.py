"""Unit tests for the MCP-side HTTP helpers in resolve_mcp_bridge.

Run: venv\\Scripts\\python.exe -m unittest discover -s tests
These tests mock urllib so no live bridge is needed.
"""

import io
import json
import os
import sys
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import resolve_mcp_bridge as rb  # noqa: E402


class _FakeResp(io.BytesIO):
    """Minimal context-manager stand-in for an urlopen response."""

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


class GetParamEncodingTests(unittest.TestCase):
    def test_special_chars_are_url_encoded(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _FakeResp(json.dumps({"ok": True}).encode("utf-8"))

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            out = rb._get("/clip/info", {"clipName": "My Clip & Co #2"})

        self.assertEqual(out, {"ok": True})
        # Spaces, & and # must be percent-encoded, not passed raw.
        self.assertIn("clipName=My+Clip+%26+Co+%232", captured["url"])
        self.assertNotIn(" ", captured["url"])
        self.assertNotIn("#", captured["url"].split("?", 1)[1])

    def test_no_params_no_querystring(self):
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _FakeResp(json.dumps({"ok": 1}).encode("utf-8"))

        with mock.patch("urllib.request.urlopen", fake_urlopen):
            rb._get("/status")
        self.assertTrue(captured["url"].endswith("/status"))


class ConnErrorTests(unittest.TestCase):
    def test_resolve_not_running_message(self):
        with mock.patch.object(rb, "_resolve_running", return_value=False):
            self.assertIn("does not appear to be running", rb._conn_error())

    def test_resolve_running_bridge_down_message(self):
        with mock.patch.object(rb, "_resolve_running", return_value=True):
            msg = rb._conn_error()
            self.assertIn("CursorBridge script isn't started", msg)

    def test_indeterminate_falls_back_generic(self):
        with mock.patch.object(rb, "_resolve_running", return_value=None):
            self.assertEqual(rb._conn_error(), rb.CONN_ERROR)


class StatusHandshakeTests(unittest.TestCase):
    def test_version_mismatch_flagged(self):
        stale = {"connected": True, "bridgeVersion": "0.0.1"}
        with mock.patch.object(rb, "_get", return_value=stale):
            out = rb.get_resolve_status()
        self.assertIn("versionMismatch", out)
        self.assertIn("ffmpeg", out)
        self.assertEqual(out["mcpExpectedBridgeVersion"], rb.EXPECTED_BRIDGE_VERSION)

    def test_matching_version_no_flag(self):
        good = {"connected": True, "bridgeVersion": rb.EXPECTED_BRIDGE_VERSION}
        with mock.patch.object(rb, "_get", return_value=good):
            out = rb.get_resolve_status()
        self.assertNotIn("versionMismatch", out)


class JobRegistryTests(unittest.TestCase):
    def _wait(self, job_id, timeout=5.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            st = rb.get_job_status(job_id)
            if st.get("state") in ("done", "error"):
                return st
            time.sleep(0.02)
        self.fail("job did not finish in time")

    def test_success_job(self):
        handle = rb._run_async("test", lambda: {"success": True, "value": 42})
        self.assertEqual(handle["state"], "queued")
        st = self._wait(handle["job_id"])
        self.assertEqual(st["state"], "done")
        self.assertEqual(st["result"], {"success": True, "value": 42})
        self.assertIsNotNone(st["started"])
        self.assertIsNotNone(st["finished"])

    def test_error_result_marks_error(self):
        handle = rb._run_async("test", lambda: {"error": "boom"})
        st = self._wait(handle["job_id"])
        self.assertEqual(st["state"], "error")
        self.assertEqual(st["error"], "boom")

    def test_exception_marks_error(self):
        def boom():
            raise ValueError("kaboom")
        handle = rb._run_async("test", boom)
        st = self._wait(handle["job_id"])
        self.assertEqual(st["state"], "error")
        self.assertIn("kaboom", st["error"])

    def test_list_jobs_includes(self):
        handle = rb._run_async("test", lambda: {"ok": 1})
        self._wait(handle["job_id"])
        ids = [j["id"] for j in rb.list_jobs()["jobs"]]
        self.assertIn(handle["job_id"], ids)

    def test_unknown_job(self):
        self.assertIn("error", rb.get_job_status("does-not-exist"))


if __name__ == "__main__":
    unittest.main()
