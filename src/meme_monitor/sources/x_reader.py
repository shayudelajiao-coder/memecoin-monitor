from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Callable, Sequence


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess[str]]


def default_runner(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)


class XReader:
    ALLOWED_COMMANDS = {"tweet", "tweets", "search", "user"}

    def __init__(self, script: str | Path = r"C:\Users\Administrator\.codex\skills\x-aggregate-data\scripts\x.py", runner: Runner = default_runner):
        self.script = str(script)
        self.runner = runner

    def read(self, command: str, target: str, extra: list[str] | None = None) -> object:
        if command not in self.ALLOWED_COMMANDS:
            raise ValueError(f"unsupported X read command: {command}")
        argv = ["py", "-3", self.script, command, target]
        if extra:
            argv.extend(extra)
        result = self.runner(argv)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or f"x.py exited with {result.returncode}")
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("x.py returned invalid JSON") from exc

