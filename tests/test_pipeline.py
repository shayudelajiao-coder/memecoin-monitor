from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from meme_monitor.config import MonitorConfig
from meme_monitor.models import Evidence, Event, SourceStatus
from meme_monitor.pipeline import MonitorPipeline
from meme_monitor.storage import JsonlStore


def alpha_event():
    return Event("alpha", "alpha", "P0", "bsc", "0xa", "ALPHA", "2026-10-11T08:00:00Z", "2026-10-11T08:00:00Z", {"volume_24h": 500000, "liquidity_usd": 200000}, [Evidence("binance_alpha", "https://binance.test", "2026-10-11T08:00:00Z", 0.9), Evidence("rpc:bsc", "https://scan.test", "2026-10-11T08:00:00Z", 0.8)])


def dex_event():
    return Event("dex", "breakout", "P1", "bsc", "0xd", "DEX", "2026-10-11T08:00:00Z", "2026-10-11T08:00:00Z", {"volume_24h": 300000, "liquidity_usd": 100000, "price_change_1h": 20}, [Evidence("dexscreener", "https://dex.test", "2026-10-11T08:00:00Z", 0.7)])


class PipelineTests(unittest.TestCase):
    def test_run_once_persists_and_renders_candidates(self):
        config = MonitorConfig(chains={"bsc": object()})
        def collector():
            return [alpha_event(), dex_event(), Event("low", "narrative", "P1", "bsc", "0xl", "LOW", "2026-10-11T08:00:00Z", "2026-10-11T08:00:00Z", {}, [])], SourceStatus("fake", True, "2026-10-11T08:00:00Z")
        with tempfile.TemporaryDirectory() as directory:
            summary = MonitorPipeline(config, JsonlStore(directory), [collector]).run_once()
            drafts = JsonlStore(directory).read_drafts()
        self.assertEqual(summary.candidates, 2)
        self.assertEqual(summary.drafts_written, 3)
        self.assertIn("thread", {row["format"] for row in drafts})
        self.assertIn("short", {row["format"] for row in drafts})


if __name__ == "__main__":
    unittest.main()

