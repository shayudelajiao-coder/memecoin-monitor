from __future__ import annotations

from datetime import datetime, timezone

from .models import Event


RISK_FLAGS = {
    "lp_removed",
    "developer_sell",
    "concentration",
    "transfer_restriction",
    "tax_anomaly",
    "privileged_owner",
    "insufficient_liquidity",
}


def _number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def score_event(event: Event) -> Event:
    if event.event_type == "social_post":
        return _score_social_post(event)
    source = 30 if any(item.source.startswith("binance") for item in event.evidence) else 25 if event.evidence else 0
    market = 0.0
    volume = _number(event.metrics.get("volume_24h"))
    liquidity = _number(event.metrics.get("liquidity_usd"))
    price_change = abs(_number(event.metrics.get("price_change_1h")))
    market += min(10.0, volume / 100000.0 * 10.0)
    market += min(10.0, liquidity / 100000.0 * 10.0)
    market += min(5.0, price_change / 20.0 * 5.0)
    propagation = min(20.0, len(event.evidence) * 7.0)
    if source == 30 and len(event.evidence) >= 2:
        propagation = min(20.0, propagation + 5.0)
    freshness = 15.0 if event.priority == "P0" else 10.0
    penalty = min(30.0, len(set(event.risk_flags) & RISK_FLAGS) * 8.0)
    event.score = round(max(0.0, min(100.0, source + market + propagation + freshness - penalty)), 2)
    event.classification = classify_score(event.score, event.risk_flags)
    return event


def _score_social_post(event: Event) -> Event:
    likes = _number(event.metrics.get("likes"))
    reposts = _number(event.metrics.get("reposts"))
    replies = _number(event.metrics.get("replies"))
    text = str(event.metrics.get("text", "")).lower()
    keyword_signal = any(keyword in text for keyword in ("launch", "listing", "alpha", "mainnet", "token", "buyback", "vault", "pool", "airdrop", "claim", "live", "上线", "发射", "合约", "回购", "空投", "领取", "主网"))
    source = 30.0 if event.evidence else 0.0
    propagation = min(20.0, likes / 100.0 + reposts / 10.0 + replies / 25.0)
    event.score = round(max(0.0, min(100.0, source + propagation + (15.0 if event.priority == "P0" else 10.0))), 2)
    # Every configured account is an editorial input, but low-signal posts stay background.
    event.classification = "short" if keyword_signal or event.score >= 45 else "background"
    return event


def classify_score(score: float, risk_flags: list[str] | None = None, major_threshold: int = 80, short_threshold: int = 60) -> str:
    if risk_flags and any(flag in RISK_FLAGS for flag in risk_flags):
        return "short" if score >= short_threshold else "background"
    if score >= major_threshold:
        return "major"
    if score >= short_threshold:
        return "short"
    return "background"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def deduplicate(events: list[Event], window_minutes: int = 45) -> list[Event]:
    selected: list[Event] = []
    for event in sorted(events, key=lambda item: (item.occurred_at, -item.score)):
        duplicate = False
        for existing in selected:
            if (event.event_type, event.chain, event.token_address.lower(), event.symbol.lower()) != (
                existing.event_type, existing.chain, existing.token_address.lower(), existing.symbol.lower()
            ):
                continue
            try:
                delta = abs((_parse_time(event.occurred_at) - _parse_time(existing.occurred_at)).total_seconds())
            except ValueError:
                delta = window_minutes * 60 + 1
            if delta <= window_minutes * 60:
                duplicate = True
                if event.score > existing.score:
                    selected[selected.index(existing)] = event
                break
        if not duplicate:
            selected.append(event)
    return selected

