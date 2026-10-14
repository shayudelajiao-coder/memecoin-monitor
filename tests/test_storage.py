from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from meme_monitor.models import Draft, SourceStatus
from meme_monitor.storage import JsonlStore


class StorageTests(unittest.TestCase):
    def test_jsonl_and_atomic_state(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JsonlStore(directory)
            store.append_draft(Draft("e1", "short", "zh", "hello"))
            store.append_health(SourceStatus("test", True, "2026-10-11T08:00:00Z"))
            store.write_state({"cursor": "10"})
            self.assertEqual(store.read_drafts()[0]["text"], "hello")
            self.assertEqual(store.read_state()["cursor"], "10")

    def test_queue_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            store = JsonlStore(directory)
            for index in range(2):
                store.append_draft(Draft(f"e{index}", "short", "zh", "hello"))
            drafts = [Draft("new", "short", "zh", "new")]
            self.assertEqual(store.enforce_queue_limit(drafts, 2), [])


if __name__ == "__main__":
    unittest.main()

