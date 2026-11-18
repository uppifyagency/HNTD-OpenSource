"""Tests for BRK audit fixes."""
import sys
import os
import unittest
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, os.path.dirname(__file__))


class TestBRK01ImportAndOrder(unittest.TestCase):
    """BRK-01: update_task_status must be importable from convex_client."""

    def test_update_task_status_importable(self):
        """update_task_status must be importable from push_results context."""
        from convex_client import update_task_status
        self.assertTrue(callable(update_task_status))

    def test_push_results_imports_update_task_status(self):
        """push_results module-level import must include update_task_status."""
        import ast

        src_path = os.path.join(os.path.dirname(__file__), "push_results.py")
        with open(src_path) as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "convex_client":
                names = [alias.name for alias in node.names]
                self.assertIn("update_task_status", names,
                              "update_task_status must be in convex_client import")
                return
        self.fail("No 'from convex_client import ...' found in push_results.py")


class TestBRK05MissingFetchFile(unittest.TestCase):
    """BRK-05: load_fetch_data must exit gracefully when fetch file is missing."""

    def test_missing_fetch_file_calls_sys_exit(self):
        """If fetch file doesn't exist, the script must call sys.exit(1)."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Patch OUTPUT_DIR so no real fetch file exists
            with patch("push_results.OUTPUT_DIR", tmpdir), \
                 patch("push_results.TASK_ID", "fake-task-id"), \
                 patch("push_results.log_pipeline_event") as mock_log, \
                 self.assertRaises(SystemExit) as ctx:
                from push_results import load_fetch_data
                load_fetch_data()

        self.assertEqual(ctx.exception.code, 1)
        mock_log.assert_called_once()
        self.assertIn("error", str(mock_log.call_args).lower())


class TestBRK07ArgParsing(unittest.TestCase):
    """BRK-07: --max-results must reject non-integer values gracefully."""

    def test_non_integer_max_results_exits(self):
        """Passing --max-results abc must exit with code 1, not ValueError."""
        import push_results

        with patch.object(sys, "argv", ["push_results.py", "fake-task", "--max-results", "abc"]), \
             patch.object(push_results, "log_pipeline_event"), \
             self.assertRaises(SystemExit) as ctx:
            push_results.main()
        self.assertEqual(ctx.exception.code, 1)


class TestBRK09RateLimit(unittest.TestCase):
    """BRK-09: HTTP 429 must be retried, not treated as a permanent client error."""

    def test_429_is_retried(self):
        """_request_with_retry must retry on 429, not raise immediately."""
        from convex_client import _request_with_retry
        import requests as req_lib

        call_count = 0

        def fake_method(url, **kwargs):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            resp.status_code = 429
            resp.text = "rate limited"
            resp.raise_for_status.side_effect = req_lib.exceptions.HTTPError(response=resp)
            return resp

        # With the fix, 429 should NOT raise immediately on first attempt
        # It should attempt max_retries times before giving up
        with patch("time.sleep"):  # don't actually sleep
            try:
                _request_with_retry(fake_method, "http://example.com", max_retries=2)
            except Exception:
                pass
        # Should have retried (more than 1 call)
        self.assertGreater(call_count, 1, "429 should trigger a retry, not immediate raise")


if __name__ == "__main__":
    unittest.main()
