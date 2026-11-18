"""Test that triage_clusters.py properly loads Pass 2 batch files."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from triage_clusters import load_all_scores, build_clusters


class TestTriagePass2Support(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.task_id = "test123"

    def _write_batch(self, filename, scores):
        path = os.path.join(self.tmpdir, filename)
        with open(path, "w") as f:
            json.dump({"scores": scores}, f)
        return path

    def test_loads_pass1_and_pass2_batches(self):
        """Should load scores from both pass1 and pass2 batch files."""
        self._write_batch(f"score-{self.task_id}-batch-0.json", [
            {"login": "alice", "score": 75},
            {"login": "bob", "score": 70},
        ])
        self._write_batch(f"score-{self.task_id}-pass2-batch-0.json", [
            {"login": "charlie", "score": 80},
            {"login": "diana", "score": 65},
        ])
        scores = load_all_scores(self.task_id, self.tmpdir)
        logins = {s["login"] for s in scores}
        self.assertEqual(logins, {"alice", "bob", "charlie", "diana"})

    def test_deduplicates_pass1_wins(self):
        """JD-08/MATH-04: ONE canonical dedup policy — the pass1 judgment wins.

        Previously triage kept the MAX score across passes (a policy unique to
        this script); the shared pass_io loader now dedups at load time with
        the same precedence used by merge/push/rank/feedback.
        """
        self._write_batch(f"score-{self.task_id}-batch-0.json", [
            {"login": "alice", "score": 75},
        ])
        self._write_batch(f"score-{self.task_id}-pass2-batch-0.json", [
            {"login": "alice", "score": 80},  # pass2 must NOT override pass1
        ])
        scores = load_all_scores(self.task_id, self.tmpdir)
        self.assertEqual(len(scores), 1)
        self.assertEqual(scores[0]["login"], "alice")
        self.assertEqual(scores[0]["score"], 75)

    def test_clusters_mixed_passes(self):
        """Clustering works correctly with devs from both passes."""
        scores = [
            {"login": "charlie", "score": 80},  # Pass 2
            {"login": "alice", "score": 75},     # Pass 1
            {"login": "bob", "score": 73},       # Pass 1
            {"login": "diana", "score": 40},     # Pass 2 (isolated)
        ]
        # Sort DESC by score (as main() does before calling build_clusters)
        scores.sort(key=lambda x: x.get("score", 0), reverse=True)
        clusters, isolated = build_clusters(scores)
        # charlie(80), alice(75), bob(73) within ±10 → 1 cluster
        self.assertEqual(len(clusters), 1)
        self.assertEqual(len(clusters[0]), 3)
        # diana(40) is isolated (>10 gap from 73)
        self.assertEqual(len(isolated), 1)
        self.assertEqual(isolated[0]["login"], "diana")


if __name__ == "__main__":
    unittest.main()
