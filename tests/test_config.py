import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from meme_monitor.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_contains_safe_defaults(self):
        path = Path(self._testMethodName + ".json")
        path.write_text(json.dumps({
            "queue_limit_per_day": 10,
            "major_threshold": 80,
            "short_threshold": 60,
            "chains": {"solana": {"enabled": True}},
        }), encoding="utf-8")
        try:
            config = load_config(path)
        finally:
            path.unlink(missing_ok=True)
        self.assertEqual(config.queue_limit_per_day, 10)
        self.assertEqual(config.major_threshold, 80)
        self.assertEqual(config.short_threshold, 60)
        self.assertTrue(config.chains["solana"].enabled)

    def test_rejects_inverted_thresholds(self):
        path = Path("invalid-config.json")
        path.write_text(json.dumps({"major_threshold": 60, "short_threshold": 80, "chains": {"x": {}}}), encoding="utf-8")
        try:
            with self.assertRaises(ValueError):
                load_config(path)
        finally:
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

