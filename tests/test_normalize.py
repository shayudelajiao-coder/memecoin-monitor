import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from meme_monitor.normalize import normalize_dex_pair, normalize_alpha_token


class NormalizeTests(unittest.TestCase):
    def test_normalize_dex_pair_preserves_chain_address_and_raw_values(self):
        pair = json.loads((Path(__file__).parent / "fixtures" / "dex_pair.json").read_text(encoding="utf-8"))
        event = normalize_dex_pair(pair, fetched_at="2026-10-11T08:00:00Z")
        self.assertEqual(event.chain, "bsc")
        self.assertEqual(event.token_address, "0xtoken")
        self.assertEqual(event.raw["priceUsd"], "0.0012")
        self.assertEqual(event.evidence[0].source, "dexscreener")

    def test_normalize_alpha_token_marks_p0(self):
        event = normalize_alpha_token({"tokenId": "id", "chainName": "BSC", "contractAddress": "0xabc", "symbol": "MEME"}, "2026-10-11T08:00:00Z")
        self.assertEqual(event.event_type, "alpha")
        self.assertEqual(event.priority, "P0")
        self.assertEqual(event.symbol, "MEME")


if __name__ == "__main__":
    unittest.main()

