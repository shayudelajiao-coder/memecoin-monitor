from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable

from .config import MonitorConfig
from .models import Draft, Event, SourceStatus
from .render import render_english_summary, render_major_thread, render_short
from .scoring import deduplicate, score_event
from .storage import JsonlStore


Collector = Callable[[], tuple[list[Event], SourceStatus]]


@dataclass(frozen=True)
class RunSummary:
    events_seen: int
    candidates: int
    drafts_written: int
    source_failures: int


class MonitorPipeline:
    def __init__(self, config: MonitorConfig, store: JsonlStore, collectors: Iterable[Collector]):
        self.config = config
        self.store = store
        self.collectors = list(collectors)

    def run_once(self) -> RunSummary:
        all_events: list[Event] = []
        failures = 0
        for collector in self.collectors:
            try:
                events, status = collector()
            except Exception as exc:  # source isolation is intentional for the monitor loop
                status = SourceStatus(getattr(collector, "__name__", "collector"), False, _utc_now(), error=str(exc), retryable=True)
                events = []
            self.store.append_health(status)
            if not status.ok:
                failures += 1
            all_events.extend(events)
        scored = [score_event(event) for event in all_events]
        selected = deduplicate(scored, self.config.dedupe_window_minutes)
        candidates = [event for event in selected if event.classification != "background"]
        existing_pending = len(self.store.read_drafts(status="pending"))
        remaining = max(0, self.config.queue_limit_per_day - existing_pending)
        drafts_written = 0
        for event in candidates[:remaining]:
            self.store.append_event(event)
            drafts = [render_major_thread(event), render_english_summary(event)] if event.classification == "major" else [render_short(event)]
            for draft in drafts:
                self.store.append_draft(draft)
                drafts_written += 1
        return RunSummary(len(all_events), len(candidates), drafts_written, failures)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

