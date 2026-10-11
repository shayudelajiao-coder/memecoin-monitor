from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from meme_monitor.models import Evidence, Event
from meme_monitor.scoring import classify_score, deduplicate, score_event


def event(event_id, occurred_at, score_type="dex", risk_flags=None):
    evidence = [Evidence("binance_alpha" if score_type == "alpha" else "dexscreener", "", occurred_at, 0.9)]
    return Event(event_id, "alpha" if score_type == "alpha" else "breakout", "P0" if score_type == "alpha" else "P1", "bsc", "0x1", "MEME", occurred_at, occurred_at, {"volume_24h": 500000, "liquidity_usd": 200000, "price_change_1h": 50}, evidence, {}, risk_flags or [])


class ScoringTests(unittest.TestCase):
    def test_major_and_short_classification(self):
        major = score_event(event("a", "2026-10-11T08:00:00Z", "alpha"))
        major.evidence.append(Evidence("rpc:bsc", "", "2026-10-11T08:00:00Z", 0.8))
        major = score_event(major)
        short = score_event(event("b", "2026-10-11T08:00:00Z"))
        self.assertEqual(major.classification, "major")
        self.assertIn(short.classification, {"short", "major"})

    def test_risk_event_cannot_be_major(self):
        risky = score_event(event("c", "2026-10-11T08:00:00Z", risk_flags=["lp_removed"]))
        self.assertNotEqual(risky.classification, "major")

    def test_deduplicate_45_minute_window(self):
        first = event("a", "2026-10-11T08:00:00Z")
        second = event("b", "2026-10-11T08:20:00Z")
        first.score, second.score = 60, 75
        selected = deduplicate([first, second], 45)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].event_id, "b")

    def test_thresholds(self):
        self.assertEqual(classify_score(80), "major")
        self.assertEqual(classify_score(60), "short")
        self.assertEqual(classify_score(59), "background")


if __name__ == "__main__":
    unittest.main()

