from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Evidence:
    source: str
    url: str
    fetched_at: str
    confidence: float
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    event_id: str
    event_type: str
    priority: str
    chain: str
    token_address: str
    symbol: str
    occurred_at: str
    fetched_at: str
    metrics: dict[str, Any] = field(default_factory=dict)
    evidence: list[Evidence] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    risk_flags: list[str] = field(default_factory=list)
    score: float = 0.0
    classification: str = "background"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["evidence"] = [item.to_dict() for item in self.evidence]
        return payload


@dataclass
class Draft:
    event_id: str
    format: str
    language: str
    text: str | list[str]
    evidence_urls: list[str] = field(default_factory=list)
    risk_flags: list[str] = field(default_factory=list)
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SourceStatus:
    source: str
    ok: bool
    fetched_at: str
    latency_ms: int = 0
    retryable: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

