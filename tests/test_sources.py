import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from meme_monitor.http import HttpClient
from meme_monitor.sources.binance_alpha import BinanceAlphaSource
from meme_monitor.sources.dexscreener import DexScreenerSource
from meme_monitor.sources.x_source import XSource


class FakeTransport:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status = status
        self.calls = []

    def __call__(self, url, timeout):
        self.calls.append(url)
        if isinstance(self.payload, bytes):
            return self.status, self.payload
        return self.status, json.dumps(self.payload).encode("utf-8")


class SourceTests(unittest.TestCase):
    def test_x_source_seeds_then_emits_new_posts(self):
        class Reader:
            def __init__(self):
                self.payloads = [
                    {"tweets": [{"id": "1", "url": "https://x.test/1", "created_at": "2026-10-11T08:00:00Z", "author": {"handle": "Pumpfun"}, "text": "GM"}]},
                    {"tweets": [
                        {"id": "2", "url": "https://x.test/2", "created_at": "2026-10-11T08:01:00Z", "author": {"handle": "Pumpfun"}, "text": "New token launch"},
                        {"id": "1", "url": "https://x.test/1", "created_at": "2026-10-11T08:00:00Z", "author": {"handle": "Pumpfun"}, "text": "GM"},
                    ]},
                ]

            def read(self, command, target, extra):
                return self.payloads.pop(0)

        with tempfile.TemporaryDirectory() as directory:
            source = XSource(Reader(), ["@Pumpfun"], Path(directory) / "x.json")
            first, status = source.collect()
            second, _ = source.collect()
        self.assertTrue(status.ok)
        self.assertEqual(first, [])
        self.assertEqual([event.symbol for event in second], ["@Pumpfun"])
        self.assertEqual(second[0].event_type, "social_post")

    def test_alpha_seeds_then_emits_only_new_ids(self):
        payload = json.loads((Path(__file__).parent / "fixtures" / "binance_alpha.json").read_text(encoding="utf-8"))
        transport = FakeTransport(payload)
        with tempfile.TemporaryDirectory() as directory:
            source = BinanceAlphaSource(HttpClient(transport=transport, retries=0), Path(directory) / "state.json", "https://alpha.test")
            first, status = source.collect()
            second, _ = source.collect()
        self.assertTrue(status.ok)
        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertEqual(len(transport.calls), 2)

    def test_alpha_emits_new_token_after_seed(self):
        first_payload = {"data": [{"tokenId": "one", "chainName": "BSC", "contractAddress": "0x1", "symbol": "ONE"}]}
        second_payload = {"data": first_payload["data"] + [{"tokenId": "two", "chainName": "BSC", "contractAddress": "0x2", "symbol": "TWO"}]}
        responses = [FakeTransport(first_payload), FakeTransport(second_payload)]
        class SequenceTransport:
            def __call__(self, url, timeout):
                current = responses.pop(0)
                return current(url, timeout)
        with tempfile.TemporaryDirectory() as directory:
            source = BinanceAlphaSource(HttpClient(transport=SequenceTransport(), retries=0), Path(directory) / "state.json", "https://alpha.test")
            source.collect()
            events, _ = source.collect()
        self.assertEqual([event.symbol for event in events], ["TWO"])

    def test_http_failure_is_retryable(self):
        transport = FakeTransport(b"bad", status=503)
        response = HttpClient(transport=transport, retries=0).get_json("https://fail.test", "test")
        self.assertFalse(response.status.ok)
        self.assertTrue(response.status.retryable)

    def test_dex_pair_normalizes(self):
        payload = {"pairs": [{"chainId": "bsc", "url": "https://dex.test", "baseToken": {"address": "0x1", "symbol": "M"}, "volume": {}, "liquidity": {}}]}
        event, status = DexScreenerSource(HttpClient(FakeTransport(payload), retries=0)).get_pair("bsc", "pair")
        self.assertTrue(status.ok)
        self.assertEqual(event.symbol, "M")


if __name__ == "__main__":
    unittest.main()

