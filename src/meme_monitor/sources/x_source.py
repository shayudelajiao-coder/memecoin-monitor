from __future__ import annotations

import json
from pathlib import Path

from ..models import Event, SourceStatus
from ..normalize import normalize_x_post
from .x_reader import XReader


class XSource:
    """Read configured public X timelines and emit only unseen posts."""

    def __init__(self, reader: XReader, accounts: list[str], state_path: str | Path, limit: int = 10):
        self.reader = reader
        self.accounts = [str(account).lstrip("@").strip() for account in accounts if str(account).strip()]
        self.state_path = Path(state_path)
        self.limit = max(1, min(int(limit), 100))

    def _read_state(self) -> dict[str, set[str]]:
        if not self.state_path.exists():
            return {}
        try:
            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            accounts = raw.get("accounts", {}) if isinstance(raw, dict) else {}
            return {str(handle): {str(tweet_id) for tweet_id in ids} for handle, ids in accounts.items() if isinstance(ids, list)}
        except (OSError, json.JSONDecodeError, AttributeError):
            return {}

    def _write_state(self, state: dict[str, set[str]]) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".tmp")
        payload = {"accounts": {handle: sorted(ids) for handle, ids in state.items()}}
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.state_path)

    def collect(self) -> tuple[list[Event], SourceStatus]:
        from ..normalize import utc_now

        fetched = utc_now()
        old_state = self._read_state()
        next_state: dict[str, set[str]] = {}
        events: list[Event] = []
        failures: list[str] = []
        seeded_accounts = 0
        for handle in self.accounts:
            try:
                payload = self.reader.read("tweets", handle, ["--limit", str(self.limit)])
                if not isinstance(payload, dict):
                    raise RuntimeError("X reader returned a non-object payload")
                if payload.get("error"):
                    raise RuntimeError(str(payload.get("error")))
                tweets = payload.get("tweets") or payload.get("data") or []
                tweets = [tweet for tweet in tweets if isinstance(tweet, dict) and tweet.get("id")]
                current_ids = {str(tweet["id"]) for tweet in tweets}
                next_state[handle] = current_ids
                if handle not in old_state:
                    seeded_accounts += 1
                    continue
                for tweet in tweets:
                    if str(tweet["id"]) in old_state.get(handle, set()):
                        continue
                    event = normalize_x_post(tweet, fetched)
                    if event is not None:
                        events.append(event)
            except Exception as exc:  # one account must not stop the rest
                failures.append(f"@{handle}: {exc}")
                next_state[handle] = old_state.get(handle, set())
        self._write_state(next_state)
        status = SourceStatus("x", not failures, fetched, error="; ".join(failures), retryable=bool(failures))
        if seeded_accounts and not events and not failures:
            return [], status
        return events, status
