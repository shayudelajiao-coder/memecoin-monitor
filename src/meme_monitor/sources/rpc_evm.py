from __future__ import annotations

import json
from typing import Any, Callable
from urllib.request import Request, urlopen


RpcTransport = Callable[[str, str, list[Any], float], Any]


def default_rpc_transport(url: str, method: str, params: list[Any], timeout: float) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "meme-monitor/0.1"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return payload.get("result")


class EvmReader:
    def __init__(self, rpc_url: str, transport: RpcTransport = default_rpc_transport, timeout: float = 10.0):
        self.rpc_url = rpc_url
        self.transport = transport
        self.timeout = timeout

    def call(self, method: str, params: list[Any]) -> Any:
        return self.transport(self.rpc_url, method, params, self.timeout)

    def block_number(self) -> int:
        return int(self.call("eth_blockNumber", []), 16)

    def get_block(self, block: int | str = "latest") -> dict[str, Any] | None:
        tag = hex(block) if isinstance(block, int) else block
        return self.call("eth_getBlockByNumber", [tag, False])

    def get_logs(self, address: str | None, from_block: int, to_block: int, topics: list[str] | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"fromBlock": hex(from_block), "toBlock": hex(to_block)}
        if address:
            params["address"] = address
        if topics:
            params["topics"] = topics
        result = self.call("eth_getLogs", [params])
        return result if isinstance(result, list) else []

