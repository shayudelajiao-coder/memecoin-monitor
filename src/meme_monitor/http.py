from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import time
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .models import SourceStatus


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class JsonResponse:
    payload: object | None
    status: SourceStatus


Transport = Callable[[str, float], tuple[int, bytes]]


def default_transport(url: str, timeout: float) -> tuple[int, bytes]:
    request = Request(url, headers={"User-Agent": "meme-monitor/0.1", "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        return int(response.status), response.read()


class HttpClient:
    def __init__(self, transport: Transport = default_transport, timeout: float = 10.0, retries: int = 2):
        self.transport = transport
        self.timeout = timeout
        self.retries = retries

    def get_json(self, url: str, source: str) -> JsonResponse:
        started = time.monotonic()
        last_error = ""
        retryable = False
        for attempt in range(self.retries + 1):
            try:
                status_code, body = self.transport(url, self.timeout)
                retryable = status_code == 429 or status_code >= 500
                if retryable and attempt < self.retries:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                if status_code < 200 or status_code >= 300:
                    last_error = f"http_{status_code}"
                    break
                try:
                    payload = json.loads(body.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError):
                    last_error = "invalid_json"
                    retryable = False
                    break
                return JsonResponse(payload, SourceStatus(source, True, utc_now(), int((time.monotonic() - started) * 1000)))
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                last_error = "timeout" if isinstance(exc, TimeoutError) else str(exc)
                retryable = True
                if attempt < self.retries:
                    time.sleep(0.05 * (attempt + 1))
                    continue
                break
        return JsonResponse(None, SourceStatus(source, False, utc_now(), int((time.monotonic() - started) * 1000), retryable, last_error))

