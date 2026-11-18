"""Test merge_fetch_batches.py merges N fetch batch files into one."""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))


class TestMergeFetchBatches(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.task_id = "test456"

    def _write_batch(self, batch_index, developers):
        path = os.path.join(self.tmpdir, f"fetch-{self.task_id}-batch-{batch_index}.json")
        with open(path, "w") as f:
            json.dump({"taskId": self.task_id, "batchIndex": batch_index, "developers": developers}, f)

    def test_merges_two_batches(self):
        from merge_fetch_batches import merge_fetch_batches

        self._write_batch(0, [{"login": "alice"}, {"login": "bob"}])
        self._write_batch(1, [{"login": "charlie"}])

        result = merge_fetch_batches(self.task_id, self.tmpdir)
        self.assertEqual(len(result), 3)
        logins = {d["login"] for d in result}
        self.assertEqual(logins, {"alice", "bob", "charlie"})

    def test_deduplicates_by_login(self):
        from merge_fetch_batches import merge_fetch_batches

        self._write_batch(0, [{"login": "alice", "followers": 10}])
        self._write_batch(1, [{"login": "alice", "followers": 20}])  # dupe

        result = merge_fetch_batches(self.task_id, self.tmpdir)
        self.assertEqual(len(result), 1)

    def test_writes_merged_file(self):
        from merge_fetch_batches import merge_fetch_batches

        self._write_batch(0, [{"login": "alice"}])
        merge_fetch_batches(self.task_id, self.tmpdir)

        merged_path = os.path.join(self.tmpdir, f"fetch-{self.task_id}.json")
        self.assertTrue(os.path.exists(merged_path))
        with open(merged_path) as f:
            data = json.load(f)
        self.assertEqual(len(data), 1)


if __name__ == "__main__":
    unittest.main()
