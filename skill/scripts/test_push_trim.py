"""Test that push_results.py trims to maxResults before pushing."""
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(__file__))
from push_results import load_all_scores


class TestMaxResultsTrim(unittest.TestCase):
    """Test the trim_to_max_results function."""

    def test_trim_reduces_to_max(self):
        """13 devs trimmed to 10 by normalizedScore."""
        from push_results import trim_to_max_results

        developers = [
            {"login": f"dev{i}", "normalizedScore": 90 - i * 5, "score": 80 - i * 3}
            for i in range(13)
        ]
        result = trim_to_max_results(developers, max_results=10)
        self.assertEqual(len(result), 10)
        # Should keep top 10 by normalizedScore
        self.assertEqual(result[0]["login"], "dev0")
        self.assertEqual(result[9]["login"], "dev9")

    def test_trim_uses_score_fallback_when_no_normalized(self):
        """If normalizedScore missing, fall back to score."""
        from push_results import trim_to_max_results

        developers = [
            {"login": f"dev{i}", "score": 90 - i * 5}
            for i in range(15)
        ]
        result = trim_to_max_results(developers, max_results=10)
        self.assertEqual(len(result), 10)
        self.assertEqual(result[0]["login"], "dev0")

    def test_trim_noop_when_under_max(self):
        """No trim when count <= maxResults."""
        from push_results import trim_to_max_results

        developers = [
            {"login": f"dev{i}", "normalizedScore": 80 - i, "score": 70}
            for i in range(5)
        ]
        result = trim_to_max_results(developers, max_results=10)
        self.assertEqual(len(result), 5)

    def test_trim_with_zero_max_returns_all(self):
        """maxResults=0 means no limit."""
        from push_results import trim_to_max_results

        developers = [{"login": f"dev{i}", "score": 50} for i in range(20)]
        result = trim_to_max_results(developers, max_results=0)
        self.assertEqual(len(result), 20)


if __name__ == "__main__":
    unittest.main()
