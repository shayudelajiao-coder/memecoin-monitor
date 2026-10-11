from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

from .config import load_config
from .http import HttpClient
from .pipeline import MonitorPipeline
from .sources.binance_alpha import BinanceAlphaSource
from .storage import JsonlStore


def build_default_pipeline(config_path: str, data_root: str) -> MonitorPipeline:
    config = load_config(config_path)
    store = JsonlStore(data_root)
    client = HttpClient()
    collectors = []
    source_config = config.sources or {}
    alpha_config = source_config.get("binance_alpha", {}) if isinstance(source_config, dict) else {}
    if alpha_config.get("enabled", True):
        collectors.append(BinanceAlphaSource(client, Path(data_root) / "alpha_state.json").collect)
    return MonitorPipeline(config, store, collectors)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meme-monitor")
    sub = parser.add_subparsers(dest="command", required=True)
    scan = sub.add_parser("scan")
    scan.add_argument("--config", default="config/watchlist.json")
    scan.add_argument("--data", default="data")
    show = sub.add_parser("show")
    show.add_argument("--status", default="pending")
    show.add_argument("--data", default="data")
    review = sub.add_parser("review")
    review.add_argument("--event", required=True)
    review.add_argument("--action", choices=["accept", "edit", "dismiss", "watchlist", "blacklist"], required=True)
    review.add_argument("--text")
    review.add_argument("--data", default="data")
    health = sub.add_parser("health")
    health.add_argument("--data", default="data")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "scan":
        summary = build_default_pipeline(args.config, args.data).run_once()
        print(json.dumps(summary.__dict__, ensure_ascii=False))
        return 0
    store = JsonlStore(args.data)
    if args.command == "show":
        print(json.dumps(store.read_drafts(args.status), ensure_ascii=False, indent=2))
        return 0
    if args.command == "health":
        print(json.dumps(store.read_jsonl(store.health_path)[-20:], ensure_ascii=False, indent=2))
        return 0
    if args.command == "review":
        rows = store.read_jsonl(store.drafts_path)
        changed = False
        for row in rows:
            if row.get("event_id") == args.event:
                row["status"] = "accepted" if args.action == "accept" else args.action
                if args.text:
                    row["text"] = args.text
                changed = True
        if not changed:
            print(f"event not found: {args.event}", file=sys.stderr)
            return 2
        temporary = store.drafts_path.with_suffix(".tmp")
        temporary.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
        temporary.replace(store.drafts_path)
        print(json.dumps({"event_id": args.event, "action": args.action}, ensure_ascii=False))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

