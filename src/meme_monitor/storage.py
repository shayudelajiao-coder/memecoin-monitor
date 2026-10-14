from __future__ import annotations

from datetime import date
import json
from pathlib import Path
from typing import Any, Iterable

from .models import Draft, Event, SourceStatus


class JsonlStore:
    def __init__(self, root: str | Path = "data"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.events_path = self.root / "events.jsonl"
        self.drafts_path = self.root / "drafts.jsonl"
        self.health_path = self.root / "health.jsonl"
        self.state_path = self.root / "state.json"

    def _append(self, path: Path, value: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(value, ensure_ascii=False) + "\n")

    def append_event(self, event: Event) -> None:
        self._append(self.events_path, event.to_dict())

    def append_draft(self, draft: Draft) -> None:
        self._append(self.drafts_path, draft.to_dict())

    def append_health(self, status: SourceStatus) -> None:
        self._append(self.health_path, status.to_dict())

    def read_jsonl(self, path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def read_events(self) -> list[dict[str, Any]]:
        return self.read_jsonl(self.events_path)

    def read_drafts(self, status: str | None = None) -> list[dict[str, Any]]:
        rows = self.read_jsonl(self.drafts_path)
        return [row for row in rows if status is None or row.get("status") == status]

    def accepted_count_today(self, day: date | None = None) -> int:
        target = (day or date.today()).isoformat()
        return sum(1 for row in self.read_drafts() if str(row.get("status", "pending")) != "dismissed" and str(row.get("event_id", "")).startswith(target))

    def write_state(self, value: dict[str, Any]) -> None:
        temporary = self.state_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self.state_path)

    def read_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def enforce_queue_limit(self, drafts: Iterable[Draft], limit: int) -> list[Draft]:
        existing = self.read_drafts(status="pending")
        remaining = max(0, limit - len(existing))
        return list(drafts)[:remaining]

