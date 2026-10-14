import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from meme_monitor.config import load_config
from meme_monitor.models import Evidence, Event, SourceStatus
from meme_monitor.pipeline import MonitorPipeline
from meme_monitor.storage import JsonlStore


class SmokeTests(unittest.TestCase):
    def test_config_fixture_pipeline_and_health(self):
        root = Path(__file__).parents[1]
        config = load_config(root / "config" / "watchlist.json")
        def collector():
            event = Event("smoke", "alpha", "P0", "bsc", "0xsmoke", "SMOKE", "2026-10-11T08:00:00Z", "2026-10-11T08:00:00Z", {"volume_24h": 100000, "liquidity_usd": 100000}, [Evidence("binance_alpha", "https://example.test", "2026-10-11T08:00:00Z", 0.9), Evidence("rpc:bsc", "https://scan.test", "2026-10-11T08:00:00Z", 0.8)])
            return [event], SourceStatus("fixture", True, "2026-10-11T08:00:00Z", 1)
        with tempfile.TemporaryDirectory() as directory:
            MonitorPipeline(config, JsonlStore(directory), [collector]).run_once()
            for path in Path(directory).iterdir():
                if path.is_file():
                    content = path.read_text(encoding="utf-8")
                    self.assertNotIn("private_key", content.lower())
                    self.assertNotIn("api_secret", content.lower())
            health = JsonlStore(directory).read_jsonl(Path(directory) / "health.jsonl")
            self.assertEqual(health[0]["source"], "fixture")


if __name__ == "__main__":
    unittest.main()

