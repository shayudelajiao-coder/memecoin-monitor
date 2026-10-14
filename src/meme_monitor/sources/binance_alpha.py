from __future__ import annotations

from pathlib import Path
import json
from typing import Any

from ..http import HttpClient
from ..models import Event, SourceStatus
from ..normalize import normalize_alpha_token


ALPHA_TOKEN_LIST_URL = "https://www.binance.com/bapi/defi/v1/public/wallet-direct/buw/wallet/cex/alpha/all/token/list"


class BinanceAlphaSource:
    def __init__(self, client: HttpClient, state_path: str | Path, url: str = ALPHA_TOKEN_LIST_URL):
        self.client = client
        self.state_path = Path(state_path)
        self.url = url

    def _read_state(self) -> set[str]:
        if not self.state_path.exists():
            return set()
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            return {str(value) for value in raw.get("token_ids", [])}
        except (OSError, json.JSONDecodeError, AttributeError):
            return set()

    def _write_state(self, token_ids: set[str]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps({"token_ids": sorted(token_ids)}, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.state_path)

    def collect(self) -> tuple[list[Event], SourceStatus]:
        response = self.client.get_json(self.url, "binance_alpha")
        if not response.status.ok:
            return [], response.status
        payload = response.payload if isinstance(response.payload, dict) else {}
        data = payload.get("data", []) if isinstance(payload, dict) else []
        tokens = data if isinstance(data, list) else []
        old_ids = self._read_state()
        current: dict[str, dict[str, Any]] = {}
        for token in tokens:
            if isinstance(token, dict) and token.get("tokenId"):
                current[str(token["tokenId"])] = token
        new_ids = set(current) - old_ids
        self._write_state(set(current))
        if not old_ids:
            return [], response.status
        events = [normalize_alpha_token(current[token_id], response.status.fetched_at) for token_id in sorted(new_ids)]
        return [event for event in events if event is not None], response.status

