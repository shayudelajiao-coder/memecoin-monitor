from __future__ import annotations

from typing import Any, Callable
from urllib.request import Request, urlopen
import json


RpcTransport = Callable[[str, str, list[Any], float], Any]


def default_rpc_transport(url: str, method: str, params: list[Any], timeout: float) -> Any:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode("utf-8")
    request = Request(url, data=body, headers={"Content-Type": "application/json", "User-Agent": "meme-monitor/0.1"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(str(payload["error"]))
    return payload.get("result")


class SolanaReader:
    def __init__(self, rpc_url: str, transport: RpcTransport = default_rpc_transport, timeout: float = 10.0):
        self.rpc_url = rpc_url
        self.transport = transport
        self.timeout = timeout

    def call(self, method: str, params: list[Any]) -> Any:
        return self.transport(self.rpc_url, method, params, self.timeout)

    def signatures_for_address(self, address: str, before: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        options: dict[str, Any] = {"limit": min(max(limit, 1), 1000)}
        if before:
            options["before"] = before
        result = self.call("getSignaturesForAddress", [address, options])
        return result if isinstance(result, list) else []

    def transaction(self, signature: str) -> dict[str, Any] | None:
        return self.call("getTransaction", [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}])

