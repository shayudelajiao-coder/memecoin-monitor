from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ChainConfig:
    name: str
    enabled: bool
    rpc_url: str = ""
    chain_id: int | None = None
    launchpad_addresses: tuple[str, ...] = ()
    program_addresses: tuple[str, ...] = ()


@dataclass(frozen=True)
class MonitorConfig:
    queue_limit_per_day: int = 10
    major_threshold: int = 80
    short_threshold: int = 60
    dedupe_window_minutes: int = 45
    chain_poll_seconds: int = 60
    bulletin_poll_seconds: int = 300
    chains: dict[str, ChainConfig] | None = None
    sources: dict[str, Any] | None = None


def _positive_int(data: dict[str, Any], key: str, default: int) -> int:
    value = data.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{key} must be a positive integer")
    return value


def load_config(path: str | Path) -> MonitorConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("configuration must be an object")
    chains_raw = raw.get("chains")
    if not isinstance(chains_raw, dict) or not chains_raw:
        raise ValueError("configuration requires a non-empty chains object")
    chains: dict[str, ChainConfig] = {}
    for key, value in chains_raw.items():
        if not isinstance(value, dict):
            raise ValueError(f"chains.{key} must be an object")
        addresses = value.get("launchpad_addresses", value.get("launchpad", {}).get("addresses", []))
        programs = value.get("program_addresses", value.get("programs", []))
        if not isinstance(addresses, list) or not all(isinstance(x, str) for x in addresses):
            raise ValueError(f"chains.{key}.launchpad_addresses must be a string list")
        if not isinstance(programs, list) or not all(isinstance(x, str) for x in programs):
            raise ValueError(f"chains.{key}.program_addresses must be a string list")
        chain_id = value.get("chain_id")
        if chain_id is not None and (not isinstance(chain_id, int) or isinstance(chain_id, bool)):
            raise ValueError(f"chains.{key}.chain_id must be an integer")
        chains[key] = ChainConfig(
            name=str(value.get("name", key)),
            enabled=bool(value.get("enabled", False)),
            rpc_url=str(value.get("rpc_url", "")),
            chain_id=chain_id,
            launchpad_addresses=tuple(addresses),
            program_addresses=tuple(programs),
        )
    major = _positive_int(raw, "major_threshold", 80)
    short = _positive_int(raw, "short_threshold", 60)
    if short >= major:
        raise ValueError("short_threshold must be lower than major_threshold")
    return MonitorConfig(
        queue_limit_per_day=_positive_int(raw, "queue_limit_per_day", 10),
        major_threshold=major,
        short_threshold=short,
        dedupe_window_minutes=_positive_int(raw, "dedupe_window_minutes", 45),
        chain_poll_seconds=_positive_int(raw, "chain_poll_seconds", 60),
        bulletin_poll_seconds=_positive_int(raw, "bulletin_poll_seconds", 300),
        chains=chains,
        sources=raw.get("sources", {}),
    )

