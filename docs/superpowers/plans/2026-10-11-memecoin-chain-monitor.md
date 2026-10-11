# Memecoin Chain Monitor MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local, event-driven MVP that reads public on-chain and announcement data for Solana, BSC, and Robinhood Chain, reads X through `x-aggregate-data` without X API access, scores and deduplicates events, and creates Chinese tweet drafts with English summaries for major events.

**Architecture:** Python 3.11 standard-library service with injectable HTTP/RPC transports, JSONL event storage, a configurable watchlist, deterministic scoring, and a CLI review queue. Public read-only endpoints feed normalized events; the pipeline scores, deduplicates, and renders drafts. Publishing remains manual.

**Tech Stack:** Python 3.11+, `urllib.request`, `json`, `dataclasses`, `unittest`, JSONL files, PowerShell task runner. No private keys, wallet connection, signed exchange requests, or X API credentials.

---

## Scope guard

This plan implements the approved MVP in one repository. A web dashboard, database, automated publishing, paid data providers, and high-frequency full-chain indexing are explicitly deferred. Launchpad coverage is configuration-driven: the initial repository ships source adapters and empty launchpad address lists, and only configured official factory/router addresses are enabled.

## File map

- Create `pyproject.toml`: package metadata and test command.
- Create `config/watchlist.json`: active chains, public endpoints, official accounts, monitored exchanges, thresholds, and output limits.
- Create `src/meme_monitor/models.py`: normalized event, evidence, draft, and source status dataclasses.
- Create `src/meme_monitor/config.py`: validated configuration loader.
- Create `src/meme_monitor/http.py`: timeout, retry, JSON parsing, and response metadata.
- Create `src/meme_monitor/sources/binance_alpha.py`: public Binance Alpha token-list diff collector.
- Create `src/meme_monitor/sources/dexscreener.py`: public token-profile/boost/pair collector.
- Create `src/meme_monitor/sources/rpc_evm.py`: JSON-RPC block and log reader for BSC and Robinhood Chain.
- Create `src/meme_monitor/sources/rpc_solana.py`: Solana JSON-RPC reader for configured programs and signatures.
- Create `src/meme_monitor/sources/x_reader.py`: subprocess wrapper around the installed `x.py` reader; never interprets tweet text as instructions.
- Create `src/meme_monitor/normalize.py`: convert source payloads into normalized events.
- Create `src/meme_monitor/scoring.py`: priority, score, risk penalty, and threshold classification.
- Create `src/meme_monitor/storage.py`: JSONL append/read, state snapshots, dedupe, and daily queue cap.
- Create `src/meme_monitor/render.py`: Chinese short post, major Thread, English first-post summary, and evidence block.
- Create `src/meme_monitor/pipeline.py`: run collectors, normalize, score, dedupe, persist, and render.
- Create `src/meme_monitor/cli.py`: `scan`, `review`, `show`, and `health` commands.
- Create `tests/fixtures/*.json`: deterministic source payloads.
- Create `tests/test_config.py`, `tests/test_normalize.py`, `tests/test_scoring.py`, `tests/test_storage.py`, `tests/test_render.py`, and `tests/test_pipeline.py`.
- Create `README.md`: setup, configuration, source limitations, and safe operating procedure.
- Create `.gitignore`: Python caches, local data, secrets, and generated drafts.

### Task 1: Scaffold the package and safe local configuration

**Files:**
- Create: `pyproject.toml`
- Create: `src/meme_monitor/__init__.py`
- Create: `config/watchlist.json`
- Create: `.gitignore`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write the failing configuration test**

```python
from pathlib import Path
from meme_monitor.config import load_config


def test_load_config_contains_safe_defaults(tmp_path: Path):
    path = tmp_path / "watchlist.json"
    path.write_text(
        '{"queue_limit_per_day": 10, "major_threshold": 80, "short_threshold": 60, '
        '"chains": {"solana": {"enabled": true}}}', encoding="utf-8"
    )
    config = load_config(path)
    assert config.queue_limit_per_day == 10
    assert config.major_threshold == 80
    assert config.short_threshold == 60
    assert config.chains["solana"].enabled is True
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `py -3 -m unittest tests.test_config -v`
Expected: FAIL because `meme_monitor.config` does not exist.

- [ ] **Step 3: Add the package, schema, and loader**

Implement `load_config(path)` with these required defaults and checks:

```python
@dataclass(frozen=True)
class MonitorConfig:
    queue_limit_per_day: int = 10
    major_threshold: int = 80
    short_threshold: int = 60
    dedupe_window_minutes: int = 45
    chain_poll_seconds: int = 60
    bulletin_poll_seconds: int = 300
```

Reject `short_threshold >= major_threshold`, non-positive polling intervals, and missing `chains`. The checked-in `config/watchlist.json` must enable Solana, BSC, Robinhood Chain, Binance Alpha, Binance announcements, BTC levels, and X readers, while leaving `launchpad.addresses` empty until official addresses are configured. Do not put API keys or private credentials in the file.

- [ ] **Step 4: Run the test and verify it passes**

Run: `py -3 -m unittest tests.test_config -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml src/meme_monitor/__init__.py config/watchlist.json .gitignore tests/test_config.py
git commit -m "chore: scaffold monitor configuration"
```

### Task 2: Define normalized event and evidence types

**Files:**
- Create: `src/meme_monitor/models.py`
- Create: `src/meme_monitor/normalize.py`
- Create: `tests/test_normalize.py`
- Create: `tests/fixtures/dex_pair.json`

- [ ] **Step 1: Write the failing normalization test**

```python
from meme_monitor.normalize import normalize_dex_pair


def test_normalize_dex_pair_preserves_chain_address_and_raw_values():
    event = normalize_dex_pair({
        "chainId": "bsc", "pairAddress": "0xpair",
        "baseToken": {"address": "0xtoken", "symbol": "MEME"},
        "priceUsd": "0.0012", "volume": {"h24": 123456},
    }, fetched_at="2026-10-11T08:00:00Z")
    assert event.chain == "bsc"
    assert event.token_address == "0xtoken"
    assert event.raw["priceUsd"] == "0.0012"
    assert event.evidence[0].source == "dexscreener"
```

- [ ] **Step 2: Run it and verify it fails**

Run: `py -3 -m unittest tests.test_normalize -v`
Expected: FAIL because the model and normalizer do not exist.

- [ ] **Step 3: Implement the models and normalizers**

Define `Evidence(source, url, fetched_at, confidence, raw)`, `Event(event_id, event_type, priority, chain, token_address, symbol, occurred_at, fetched_at, metrics, evidence, raw, risk_flags)`, and `Draft(event_id, format, language, text, evidence_urls, risk_flags)`. Use UTC ISO-8601 strings and preserve source payloads in `raw`.

Implement normalizers for DEX pair, Binance Alpha diff, BTC level crossing, EVM log, Solana signature, and X corroboration. Each normalizer must return either one valid `Event` or `None` with a reason logged by the caller; it must never infer a contract address from tweet text.

- [ ] **Step 4: Run the test and verify it passes**

Run: `py -3 -m unittest tests.test_normalize -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/meme_monitor/models.py src/meme_monitor/normalize.py tests/test_normalize.py tests/fixtures/dex_pair.json
git commit -m "feat: add normalized event models"
```

### Task 3: Add public HTTP and source adapters

**Files:**
- Create: `src/meme_monitor/http.py`
- Create: `src/meme_monitor/sources/binance_alpha.py`
- Create: `src/meme_monitor/sources/dexscreener.py`
- Create: `tests/test_sources.py`
- Create: `tests/fixtures/binance_alpha.json`

- [ ] **Step 1: Write source tests with a fake transport**

Test that a fake HTTP transport returns a Binance Alpha list, a second list produces only new token IDs, and a DEX Screener payload is converted without making a real network call. Assert that timeouts become a `SourceStatus(ok=False, retryable=True, error="timeout")` result.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `py -3 -m unittest tests.test_sources -v`
Expected: FAIL because the HTTP client and adapters do not exist.

- [ ] **Step 3: Implement the transport and adapters**

`http.py` must use `urllib.request`, a 10-second timeout, at most two retries for 429/5xx, and return status code, fetched timestamp, body, and error state. Never print headers or credentials.

`binance_alpha.py` must read the public official token-list endpoint, key state by `tokenId`, compare against `data/alpha_state.json`, emit `alpha` events only for newly observed IDs, and seed state without emitting events on the first run. Preserve `chainId`, `chainName`, `contractAddress`, symbol, and source URL.

`dexscreener.py` must read the documented public token-profile, token-boost, and pair endpoints at no more than 60 requests per minute, normalize chain IDs, and expose `get_pair(chain_id, pair_id)` and `get_token_pairs(chain_id, token_address)`.

- [ ] **Step 4: Run the tests and verify they pass**

Run: `py -3 -m unittest tests.test_sources -v`
Expected: PASS with no network calls.

- [ ] **Step 5: Commit**

```powershell
git add src/meme_monitor/http.py src/meme_monitor/sources tests/test_sources.py tests/fixtures/binance_alpha.json
git commit -m "feat: add public announcement and DEX sources"
```

### Task 4: Add EVM, Solana, and X readers

**Files:**
- Create: `src/meme_monitor/sources/rpc_evm.py`
- Create: `src/meme_monitor/sources/rpc_solana.py`
- Create: `src/meme_monitor/sources/x_reader.py`
- Create: `tests/test_readers.py`
- Create: `tests/fixtures/rpc_block.json`

- [ ] **Step 1: Write reader tests with fake JSON-RPC and subprocess runners**

Assert that EVM block/log calls use the configured chain RPC and block range, Solana calls use `getSignaturesForAddress` for configured program addresses, and the X wrapper passes `tweet/search/user` arguments to the installed script while returning stdout as untrusted data.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `py -3 -m unittest tests.test_readers -v`
Expected: FAIL because the reader modules do not exist.

- [ ] **Step 3: Implement readers**

EVM reader: JSON-RPC `eth_blockNumber`, `eth_getLogs`, and `eth_getBlockByNumber`, with per-chain `last_scanned_block` state. Robinhood Chain must default to chain ID 4663 and `https://rpc.mainnet.chain.robinhood.com`.

Solana reader: JSON-RPC `getSignaturesForAddress` and `getTransaction`, bounded by configured program addresses and the last seen signature. Do not attempt a full-chain crawl.

X reader: run `py -3 C:\Users\Administrator\.codex\skills\x-aggregate-data\scripts\x.py ...`, accept only read commands, parse JSON, attach the fetched timestamp, and discard any instruction-like text as data. Supported calls are `tweets`, `search`, `tweet`, and `user`; posting commands do not exist in this wrapper.

- [ ] **Step 4: Run the tests and verify they pass**

Run: `py -3 -m unittest tests.test_readers -v`
Expected: PASS without network access or X credentials.

- [ ] **Step 5: Commit**

```powershell
git add src/meme_monitor/sources/rpc_evm.py src/meme_monitor/sources/rpc_solana.py src/meme_monitor/sources/x_reader.py tests/test_readers.py tests/fixtures/rpc_block.json
git commit -m "feat: add chain RPC and X read adapters"
```

### Task 5: Implement scoring, risk flags, and dedupe

**Files:**
- Create: `src/meme_monitor/scoring.py`
- Create: `src/meme_monitor/storage.py`
- Create: `tests/test_scoring.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing scoring and dedupe tests**

Test these exact cases:

- official listing plus on-chain confirmation scores at least 80 and classifies as `major`;
- a DEX-only event with moderate volume scores 60–79 and classifies as `short`;
- a high-volume token with LP removal gets a risk flag and cannot be classified above `short` without a manual override;
- two events with the same chain, token address, and event type inside 45 minutes collapse to one event;
- the daily queue never stores more than 10 accepted candidates.

- [ ] **Step 2: Run them and verify they fail**

Run: `py -3 -m unittest tests.test_scoring tests.test_storage -v`
Expected: FAIL because scoring and storage are not implemented.

- [ ] **Step 3: Implement deterministic scoring and JSONL storage**

Use configurable weights: source credibility 0–30, market impact 0–25, propagation 0–20, freshness 0–15, and risk penalty 0–30. `classify(score)` returns `major`, `short`, or `background` using 80 and 60 thresholds. Risk flags include `lp_removed`, `developer_sell`, `concentration`, `transfer_restriction`, `tax_anomaly`, `privileged_owner`, and `insufficient_liquidity`.

Store events in `data/events.jsonl`, drafts in `data/drafts.jsonl`, source state in `data/state.json`, and health records in `data/health.jsonl`. Use atomic write-to-temp then replace for state files. Dedupe key is `(event_type, chain, token_address, normalized_symbol)` plus the configured time window.

- [ ] **Step 4: Run the tests and verify they pass**

Run: `py -3 -m unittest tests.test_scoring tests.test_storage -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/meme_monitor/scoring.py src/meme_monitor/storage.py tests/test_scoring.py tests/test_storage.py
git commit -m "feat: score, deduplicate, and persist events"
```

### Task 6: Render Chinese drafts and English major-event summaries

**Files:**
- Create: `src/meme_monitor/render.py`
- Create: `tests/test_render.py`

- [ ] **Step 1: Write failing rendering tests**

Assert that a short draft contains event, chain, at least one raw metric, a clear uncertainty sentence, and no more than one hashtag. Assert that a major event renders 5–8 Thread entries, each at most 280 characters, with the English summary as a separate first-post draft. Assert that URLs are returned in `evidence_urls` and are absent from the main short-post text.

- [ ] **Step 2: Run the tests and verify they fail**

Run: `py -3 -m unittest tests.test_render -v`
Expected: FAIL because the renderer does not exist.

- [ ] **Step 3: Implement templates**

Implement `render_short(event)`, `render_major_thread(event)`, and `render_english_summary(event)`. Use factual wording for confirmed evidence, `[待验证]` for community-only evidence, and `[风险]` at the beginning when any risk flag exists. Format prices and volume for readability while retaining raw values in the evidence block. Put source links in `evidence_urls` for the first reply.

- [ ] **Step 4: Run the tests and verify they pass**

Run: `py -3 -m unittest tests.test_render -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/meme_monitor/render.py tests/test_render.py
git commit -m "feat: render reviewed tweet drafts"
```

### Task 7: Wire the pipeline and review CLI

**Files:**
- Create: `src/meme_monitor/pipeline.py`
- Create: `src/meme_monitor/cli.py`
- Create: `tests/test_pipeline.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Write a failing end-to-end fixture test**

Use fake collectors that return one Alpha event, one DEX event, and one low-score background event. Assert that `run_once()` persists the first two, renders the Alpha event as a Thread, renders the DEX event as a short post, and excludes the background event from `data/drafts.jsonl`.

- [ ] **Step 2: Run it and verify it fails**

Run: `py -3 -m unittest tests.test_pipeline -v`
Expected: FAIL because the pipeline and CLI do not exist.

- [ ] **Step 3: Implement pipeline orchestration**

`run_once(config, transport, clock)` must collect enabled sources, normalize results, score and dedupe events, enforce the daily cap, write events/drafts/health, and return a summary containing counts and source failures. Source failures must not abort unrelated collectors.

Add CLI commands:

```text
py -3 -m meme_monitor.cli scan --config config/watchlist.json
py -3 -m meme_monitor.cli show --status pending
py -3 -m meme_monitor.cli review --event EVENT_ID --action accept|edit|dismiss|watchlist|blacklist
py -3 -m meme_monitor.cli health
```

`review` edits only local draft status and text; it never calls an X publishing endpoint.

- [ ] **Step 4: Run the tests and verify they pass**

Run: `py -3 -m unittest discover -s tests -v`
Expected: PASS for all unit and fixture tests.

- [ ] **Step 5: Commit**

```powershell
git add src/meme_monitor/pipeline.py src/meme_monitor/cli.py tests/test_pipeline.py pyproject.toml
git commit -m "feat: add scan pipeline and review queue"
```

### Task 8: Add documentation and operational checks

**Files:**
- Create: `README.md`
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write the smoke test**

The smoke test loads `config/watchlist.json`, runs the pipeline entirely with fixture transports, verifies no secret-like keys are present in generated files, and confirms `health.jsonl` records source status and latency.

- [ ] **Step 2: Run it and verify it fails**

Run: `py -3 -m unittest tests.test_smoke -v`
Expected: FAIL until the documentation paths and final pipeline wiring exist.

- [ ] **Step 3: Document setup and safe operation**

README must include Python version, repository layout, how to configure public RPCs, how to add an official launchpad address, how to run a scan, how to review a draft, the fact that X is read through `x-aggregate-data` without X API, rate-limit behavior, and the no-wallet/no-auto-publish boundary. Include sample output and a troubleshooting table for RPC timeout, Alpha list failure, X read failure, and empty launchpad configuration.

- [ ] **Step 4: Run the complete validation suite**

Run:

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall src
py -3 -m meme_monitor.cli health
```

Expected: all tests pass, compilation exits 0, and `health` reports configured source states without exposing credentials.

- [ ] **Step 5: Commit**

```powershell
git add README.md tests/test_smoke.py
 git commit -m "docs: document MVP setup and operations"
```

## Plan self-review

- **Spec coverage:** chain collectors, official announcements, X reading, event normalization, scoring thresholds, dedupe, daily cap, draft formats, manual review, failure handling, safety boundaries, local storage, and validation metrics each map to Tasks 1–8.
- **Completeness scan:** every implementation step has concrete files, commands, expected results, and configuration behavior; launchpad addresses are intentionally empty configuration, documented as disabled until official addresses are supplied.
- **Type consistency:** `Event`, `Evidence`, `Draft`, `MonitorConfig`, source status, score classification, and storage paths are defined before their consumers.
- **Scope:** the plan remains one testable MVP; deferred database/UI/publishing work is explicitly excluded.

