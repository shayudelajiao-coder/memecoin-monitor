from pathlib import Path
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from meme_monitor.sources.rpc_evm import EvmReader
from meme_monitor.sources.rpc_solana import SolanaReader
from meme_monitor.sources.x_reader import XReader


class RpcTransport:
    def __init__(self):
        self.calls = []

    def __call__(self, url, method, params, timeout):
        self.calls.append((url, method, params))
        if method == "eth_blockNumber":
            return "0x10"
        if method == "eth_getBlockByNumber":
            return {"number": "0x10", "hash": "0xblock"}
        if method == "eth_getLogs":
            return [{"address": "0xcontract", "transactionHash": "0xtx"}]
        if method == "getSignaturesForAddress":
            return [{"signature": "sig", "slot": 10}]
        if method == "getTransaction":
            return {"slot": 10}
        raise AssertionError(method)


class ReaderTests(unittest.TestCase):
    def test_evm_reader_uses_hex_blocks(self):
        transport = RpcTransport()
        reader = EvmReader("https://bsc.test", transport=transport)
        self.assertEqual(reader.block_number(), 16)
        self.assertEqual(reader.get_logs("0xcontract", 1, 16)[0]["transactionHash"], "0xtx")
        self.assertEqual(transport.calls[1][2][0]["fromBlock"], "0x1")

    def test_solana_reader_bounds_signature_limit(self):
        transport = RpcTransport()
        reader = SolanaReader("https://sol.test", transport=transport)
        result = reader.signatures_for_address("program", limit=5000)
        self.assertEqual(result[0]["signature"], "sig")
        self.assertEqual(transport.calls[0][2][1]["limit"], 1000)

    def test_x_reader_allows_read_commands_and_returns_json(self):
        calls = []
        def runner(argv):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, '{"data": [{"id": "1", "text": "hello"}]}', "")
        reader = XReader(script="x.py", runner=runner)
        payload = reader.read("search", "from:binance", ["--limit", "1"])
        self.assertEqual(payload["data"][0]["id"], "1")
        self.assertIn("search", calls[0])
        with self.assertRaises(ValueError):
            reader.read("post", "hello")


if __name__ == "__main__":
    unittest.main()

