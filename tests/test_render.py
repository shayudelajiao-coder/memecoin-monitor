from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from meme_monitor.models import Evidence, Event
from meme_monitor.render import render_english_summary, render_major_thread, render_short


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.event = Event(
            "e1", "alpha", "P0", "bsc", "0xabc", "MEME", "2026-10-11T08:00:00Z", "2026-10-11T08:01:00Z",
            {"price_usd": "0.1", "volume_24h": 100000, "liquidity_usd": 50000, "price_change_1h": 20},
            [Evidence("binance_alpha", "https://binance.test", "2026-10-11T08:01:00Z", 0.95)], {}, [], 85, "major"
        )

    def test_short_has_metrics_and_no_main_url(self):
        draft = render_short(self.event)
        self.assertIn("MEME", draft.text)
        self.assertIn("100000", draft.text)
        self.assertNotIn("https://binance.test", draft.text)
        self.assertEqual(draft.evidence_urls, ["https://binance.test"])

    def test_major_thread_is_5_to_8_posts_and_limited(self):
        draft = render_major_thread(self.event)
        self.assertGreaterEqual(len(draft.text), 5)
        self.assertLessEqual(len(draft.text), 8)
        self.assertTrue(all(len(post) <= 280 for post in draft.text))

    def test_english_summary_is_separate(self):
        draft = render_english_summary(self.event)
        self.assertEqual(draft.language, "en")
        self.assertLessEqual(len(draft.text), 280)


if __name__ == "__main__":
    unittest.main()

