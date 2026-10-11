from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import re
from typing import Any

from .models import Evidence, Event


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _event_id(event_type: str, chain: str, address: str, occurred_at: str) -> str:
    raw = "|".join((event_type, chain.lower(), address.lower(), occurred_at))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _address(payload: dict[str, Any], key: str = "address") -> str:
    value = payload.get(key) or payload.get("tokenAddress") or payload.get("contractAddress") or ""
    return str(value)


def normalize_dex_pair(pair: dict[str, Any], fetched_at: str | None = None) -> Event | None:
    chain = str(pair.get("chainId", "")).lower()
    base = pair.get("baseToken") or {}
    address = str(base.get("address", ""))
    if not chain or not address:
        return None
    fetched = fetched_at or utc_now()
    occurred = str(pair.get("pairCreatedAt") or fetched)
    if occurred.isdigit():
        occurred = datetime.fromtimestamp(int(occurred) / 1000, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    evidence = Evidence("dexscreener", str(pair.get("url", "")), fetched, 0.7, dict(pair))
    volume = pair.get("volume") if isinstance(pair.get("volume"), dict) else {}
    liquidity = pair.get("liquidity") if isinstance(pair.get("liquidity"), dict) else {}
    symbol = str(base.get("symbol", "UNKNOWN"))
    return Event(
        event_id=_event_id("breakout", chain, address, occurred),
        event_type="breakout",
        priority="P1",
        chain=chain,
        token_address=address,
        symbol=symbol,
        occurred_at=occurred,
        fetched_at=fetched,
        metrics={
            "price_usd": pair.get("priceUsd"),
            "volume_24h": volume.get("h24"),
            "liquidity_usd": liquidity.get("usd"),
            "price_change_1h": (pair.get("priceChange") or {}).get("h1") if isinstance(pair.get("priceChange"), dict) else None,
        },
        evidence=[evidence],
        raw=dict(pair),
    )


def normalize_alpha_token(token: dict[str, Any], fetched_at: str | None = None) -> Event | None:
    chain = str(token.get("chainName") or token.get("chainId") or "").lower()
    address = str(token.get("contractAddress") or "")
    token_id = str(token.get("tokenId") or address)
    if not chain or not token_id:
        return None
    fetched = fetched_at or utc_now()
    symbol = str(token.get("symbol") or token.get("name") or "UNKNOWN")
    evidence = Evidence("binance_alpha", str(token.get("url", "")), fetched, 0.95, dict(token))
    return Event(
        event_id=_event_id("alpha", chain, address or token_id, fetched),
        event_type="alpha",
        priority="P0",
        chain=chain,
        token_address=address,
        symbol=symbol,
        occurred_at=fetched,
        fetched_at=fetched,
        metrics={"token_id": token_id},
        evidence=[evidence],
        raw=dict(token),
    )


def normalize_btc_crossing(symbol: str, price: float, level: float, direction: str, fetched_at: str | None = None) -> Event:
    fetched = fetched_at or utc_now()
    evidence = Evidence("market_data", "", fetched, 0.9, {"price": price, "level": level, "direction": direction})
    return Event(
        event_id=_event_id("breakout", "bitcoin", symbol, fetched),
        event_type="breakout",
        priority="P0",
        chain="bitcoin",
        token_address=symbol,
        symbol=symbol,
        occurred_at=fetched,
        fetched_at=fetched,
        metrics={"price": price, "level": level, "direction": direction},
        evidence=[evidence],
        raw=evidence.raw,
    )


def normalize_evm_log(log: dict[str, Any], chain: str, event_type: str = "narrative", fetched_at: str | None = None) -> Event | None:
    address = str(log.get("address", ""))
    tx_hash = str(log.get("transactionHash", ""))
    if not address or not tx_hash:
        return None
    fetched = fetched_at or utc_now()
    evidence = Evidence(f"rpc:{chain}", "", fetched, 0.85, dict(log))
    return Event(
        event_id=_event_id(event_type, chain, address, tx_hash),
        event_type=event_type,
        priority="P1",
        chain=chain,
        token_address=address,
        symbol="UNKNOWN",
        occurred_at=fetched,
        fetched_at=fetched,
        metrics={"transaction_hash": tx_hash, "block_number": log.get("blockNumber")},
        evidence=[evidence],
        raw=dict(log),
    )


def normalize_solana_signature(signature: dict[str, Any], program: str, fetched_at: str | None = None) -> Event | None:
    signature_id = str(signature.get("signature", ""))
    if not signature_id:
        return None
    fetched = fetched_at or utc_now()
    evidence = Evidence("rpc:solana", "", fetched, 0.8, dict(signature))
    return Event(
        event_id=_event_id("narrative", "solana", program, signature_id),
        event_type="narrative",
        priority="P1",
        chain="solana",
        token_address=program,
        symbol="UNKNOWN",
        occurred_at=fetched,
        fetched_at=fetched,
        metrics={"signature": signature_id, "slot": signature.get("slot")},
        evidence=[evidence],
        raw=dict(signature),
    )


def normalize_x_corroboration(tweet: dict[str, Any], fetched_at: str | None = None) -> Evidence:
    fetched = fetched_at or utc_now()
    text = str(tweet.get("text", ""))
    return Evidence("x", str(tweet.get("url", "")), fetched, 0.5, {"id": tweet.get("id"), "text": text})

