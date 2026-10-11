from __future__ import annotations

from .models import Draft, Event


def _metric(event: Event, key: str, label: str) -> str:
    value = event.metrics.get(key)
    return f"{label}{value}" if value not in (None, "") else ""


def _risk_text(event: Event) -> str:
    return f"[风险] {', '.join(event.risk_flags)}" if event.risk_flags else "风险：暂无已确认风险，仍需自行核实。"


def _evidence_urls(event: Event) -> list[str]:
    return list(dict.fromkeys(item.url for item in event.evidence if item.url))


def render_short(event: Event) -> Draft:
    verification = "已多源验证" if len(event.evidence) >= 2 else "当前为单一来源，等待交叉验证"
    metrics = [
        _metric(event, "price_usd", "价格 $"),
        _metric(event, "volume_24h", "24h成交量 $"),
        _metric(event, "liquidity_usd", "流动性 $"),
        _metric(event, "price_change_1h", "1h变化 "),
    ]
    metric_text = "；".join(item for item in metrics if item)
    prefix = f"[风险] " if event.risk_flags else ""
    text = (
        f"{prefix}{event.chain.upper()} {event.symbol} 出现{event.event_type}信号。"
        f" {metric_text or '链上指标正在变化'}。"
        f" {verification}。{_risk_text(event)}"
    )
    return Draft(event.event_id, "short", "zh", text, _evidence_urls(event), list(event.risk_flags))


def render_major_thread(event: Event) -> Draft:
    urls = _evidence_urls(event)
    evidence_text = "；".join(urls) if urls else "来源链接待补充"
    lines = [
        f"{event.chain.upper()} | {event.symbol}：这次信号值得关注。评分 {event.score:.0f}/100。",
        f"发生了什么：事件类型为 {event.event_type}，发生时间 {event.occurred_at}。",
        f"关键数据：{_metric(event, 'price_usd', '价格 $')} {_metric(event, 'volume_24h', '24h成交量 $')} {_metric(event, 'liquidity_usd', '流动性 $')}。",
        f"证据：{len(event.evidence)} 个来源，状态为{'多源验证' if len(event.evidence) >= 2 else '待交叉验证'}。",
        f"为什么重要：它可能影响当前叙事和短线资金关注，但不代表后续价格方向。",
        f"风险检查：{', '.join(event.risk_flags) if event.risk_flags else '暂未发现已确认风险，合约和流动性仍需自行核实'}。",
        f"TL;DR：{event.symbol} 出现值得跟踪的链上信号；当前结论是信息整理，不是买卖建议。",
        "后续会继续跟踪成交量、流动性、持仓和官方消息变化。",
    ]
    lines = [line[:280] for line in lines]
    # URLs stay in evidence_urls so the main thread can be published without link suppression.
    return Draft(event.event_id, "thread", "zh", lines, urls, list(event.risk_flags))


def render_english_summary(event: Event) -> Draft:
    risk = ", risk flags: " + ", ".join(event.risk_flags) if event.risk_flags else ", no confirmed risk flag yet"
    text = (
        f"{event.chain.upper()} {event.symbol}: a {event.event_type} signal was detected "
        f"at {event.occurred_at}. Score {event.score:.0f}/100{risk}. "
        "This is monitoring data, not financial advice."
    )
    return Draft(event.event_id, "summary", "en", text[:280], _evidence_urls(event), list(event.risk_flags))

