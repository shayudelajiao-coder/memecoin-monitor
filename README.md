# Memecoin Chain Monitor MVP

这是一个本地运行的链上热点监控与 X 推文草稿工具。它读取公开只读数据，解析 Solana、BSC、Robinhood Chain、币安 Alpha、BTC 点位和 X 公开信息，生成中文短推或重大事件 Thread。发布始终由人工完成。

## 安全边界

- 不保存私钥，不连接钱包，不执行交易。
- 不调用 X API；X 公开内容通过本机 `x-aggregate-data` skill 的 `x.py` 读取。
- 币安和链上只使用公开只读接口，不需要交易权限。
- 事件草稿区分事实、分析和推测，不承诺收益。

## 安装

需要 Python 3.10 或更高版本。PowerShell：

```powershell
Set-Location D:\memecoin-monitor
py -3 -m pip install -e .
```

## 配置

编辑 `config/watchlist.json`：

- `chains` 配置 RPC、链 ID 和启用状态；Robinhood Chain 主网默认是 Chain ID 4663。
- `launchpad_addresses` 和 Solana `program_addresses` 只填写确认过的官方合约。
- `sources.btc_levels.levels_usd` 填写希望监控的 BTC 关键点位。
- `sources.x_accounts` 和 `sources.x_queries` 填写需要读取的公开账号或搜索语法。

启动时不启用空的发射台地址表，避免把未知合约当成官方来源。

## 运行

```powershell
Set-Location D:\memecoin-monitor
py -3 -m pip install -e .
py -3 -m meme_monitor.cli scan --config config/watchlist.json --data data
py -3 -m meme_monitor.cli show --status pending --data data
py -3 -m meme_monitor.cli health --data data
```

扫描结果写入 `data/events.jsonl`、`data/drafts.jsonl` 和 `data/health.jsonl`。普通事件生成 `short` 草稿，重大事件生成中文 `thread` 和独立英文 `summary`。来源 URL 放在证据字段中，方便人工审核后放到第一条回复。

配置了 `sources.x_accounts` 后，扫描会通过 `x-aggregate-data` 读取这些账号的最近公开推文。第一次扫描只建立 `data/x_state.json` 基线；之后只处理新推文，并根据发射、上币、回购、Vault、流动性、活动和互动量筛选草稿。X 内容只作为社媒信号，仍需用链上数据交叉验证。

审核示例：

```powershell
py -3 -m meme_monitor.cli review --event EVENT_ID --action accept --data data
py -3 -m meme_monitor.cli review --event EVENT_ID --action edit --text "修改后的草稿" --data data
```

## 数据源和限制

- 币安 Alpha 首次扫描只保存列表状态，不批量生成历史上新事件；后续差异才会进入队列。
- DEX Screener、Blockscout 和公开 RPC 有限流或延迟，健康日志会记录失败和延迟。
- X 读取失败时，链上事实仍可生成，但事件会标记未完成社交验证。
- 未配置官方发射台地址时，系统不会猜测或抓取未知发射台。
- MVP 使用 JSONL，不适合高频多实例部署；后续再升级数据库和网页面板。

## 测试

```powershell
py -3 -m unittest discover -s tests -v
py -3 -m compileall src
```

测试使用假传输和固定 fixture，不会请求真实 RPC、币安或 X。

