from __future__ import annotations

from ..http import HttpClient
from ..models import Event, SourceStatus
from ..normalize import normalize_dex_pair


class DexScreenerSource:
    def __init__(self, client: HttpClient):
        self.client = client

    def get_pair(self, chain_id: str, pair_id: str) -> tuple[Event | None, SourceStatus]:
        url = f"https://api.dexscreener.com/latest/dex/pairs/{chain_id}/{pair_id}"
        response = self.client.get_json(url, "dexscreener")
        if not response.status.ok:
            return None, response.status
        payload = response.payload if isinstance(response.payload, dict) else {}
        pairs = payload.get("pairs", []) if isinstance(payload, dict) else []
        pair = pairs[0] if isinstance(pairs, list) and pairs and isinstance(pairs[0], dict) else None
        return normalize_dex_pair(pair, response.status.fetched_at) if pair else None, response.status

    def get_token_pairs(self, chain_id: str, token_address: str) -> tuple[list[Event], SourceStatus]:
        url = f"https://api.dexscreener.com/token-pairs/v1/{chain_id}/{token_address}"
        response = self.client.get_json(url, "dexscreener")
        if not response.status.ok:
            return [], response.status
        pairs = response.payload if isinstance(response.payload, list) else []
        events = [normalize_dex_pair(pair, response.status.fetched_at) for pair in pairs if isinstance(pair, dict)]
        return [event for event in events if event is not None], response.status

