# 国家队公开资金跟踪 → 沪深300成分股研究 → ETF基准验证

项目目标：跟踪公开证据支持的中央汇金等国家队持仓变动，以及**固定四只沪深300ETF**（510300、510310、510330、159919）真实清算份额、NAV与5日资金强度；再映射成分股潜在配置敞口，验证是否比直接买沪深300ETF更有成本后超额收益。原三日技术追涨模型已降为历史研究分支。

## 已真实跑通（2026-10-28）

- [真实四ETF份额/NAV原始记录](records/national_team_etf/2026-10-28/40702172792-a1.json)：4只基金、7个连续交易日；2026-10-27整体净申购份额×当日NAV代理为**+56.12203530亿元**，不是国家队个人账户净买入。
- [独立跨运行合并](records/national_team_merged/2026-10-28/40702572594-a1.json)：6份有出处的原始记录、0个同日同证券金额冲突、7个四ETF齐备交易日。
- [真实股票研究排名](records/national_team_watch/2026-10-28/40702172792-a1.json)：中证指数公开CSI300权重、真实个股历史成交额与相对强度；首次30只大权重股票覆盖42.19%的指数权重。它是**指数权重代理，不是ETF真实PCF、不是中央汇金逐股订单**。
- [独立红队历史记录与合成反例测试](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40704384352)包括原始四ETF逐笔数据资金值重算及故意篡改后的失败测试。新的[SSE带超时原生接口](national_team/sse_direct.py)、150只股票研究池、[S1/S2事件冻结](national_team/paper_events.py)、[纸面收益追踪](national_team/live_paper_tracker.py)和[独立审计门槛](national_team/audit_gate.py)需以其**最新对应SHA的实际Actions运行**为准。

**尚待验证**：基金管理人原始PCF（当前[官方HTML采集尝试](records/national_team_pcf/2026-10-28/40702172792-a1.json)尚未解析出完整日期和成分）；国家队法定主体真实增减持、原始两个沪深300流通市值分母、正式净值与拆并事件交叉核对、真实未触碰5/10/20交易日S0/S1/S2成本后超额收益。不得把“单测通过”当成“策略稳定盈利”。

## 最新审计和代码入口

[2026-10-28 E2E对抗式审计](wiki/audits/AUD-2026-10-28-e2e-release-gate.md) · [原始四ETF指标合同](wiki/data/original-four-etf-indicator.md) · [主线决策ADR-0004](wiki/decisions/ADR-0004-stock-selection-after-flow.md) · [持续运行与真实数据留档Actions](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-live.yml) · [独立算术单测](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-factors.yml)。

## Knowledge base / 第二大脑（Agent先读这里）

**[MOC.md — 总索引](MOC.md)** · [AGENTS.md — Agent接手规则](AGENTS.md) · [KNOWLEDGE.md — LLM Wiki协议](KNOWLEDGE.md) · [最新运行自动简报](wiki/compiled/briefing.md) · [模型版本史](wiki/models/registry.md) · [完整运行账本](wiki/indices/runs.md) · [全部Git提交索引](wiki/indices/commits.md) · [历史升级/失败日志](wiki/log.md)

本仓库采用 LLM Wiki 的三层结构：`records/` 原始证据不回写，`wiki/` 由Agent持续综合，`AGENTS.md`/ `KNOWLEDGE.md` 管理每轮升级。运行后自动重建 `wiki/indices/` 和 `wiki/compiled/`，模型变更还必须更新实验、版本、决策、事故与维护日志。**当前仍是研究态，不能发可执行买卖指令。**

A **real GitHub Actions-powered** research prototype with fail-closed controls. Uses actual third-party market data; never places broker orders.

## Verified execution (2026-10-28)
- ✅ GitHub App authorized; connector commits succeeded.
- ✅ Actions installation and deterministic tests succeeded.
- ✅ Real historical data fetched and validated for 12 fixed watchlist stocks (not a comprehensive market screen).
- ✅ AKQuant API smoke ran; this **is NOT the three-day strategy's engine**.
- ✅ Custom three-day OHLC exploratory replay ran on 45 trades and QuantStats run completed in [successful action 40681563446](../../actions/runs/40681563446).
- ⚠️ This preliminary, **biased** research sample: 42.22% profitable, -0.277% mean per trade after approximate costs. There is no out-of-sample validation or true intraday T+3 14:50 executable-price modeling.
- ⚠️ Current implementation uses a **fixed 12-stock fallback watchlist** when full-market snapshot fails; it is not whole-market selection.
- ✅ GitHub Actions now commits individual run records and the full observed research replay under [records/](records/); records include code SHA, input hashes and frozen signal IDs. This is **research execution evidence**, not proof of real orders. The earliest persisted full replay is [2026-10-28 close run 40683070796](records/2026-10-28/close/40683070796-a1.json).
- ✅ Added a chronological six-month holdout *diagnostic* with a 10-calendar-day embargo, plus separate T+3 locked-limit-down censoring and no fake reentry.
- ⚠️ Backtest is not independent OOS: the 12 currently-surviving symbols are a fixed, ex-post universe; daily OHLC cannot verify 14:50 execution.
- ⚠️ Real market breadth, financing/margin series and four ETF share/NAV freshness checks are not yet validated. Absent data are recorded as FAILED/NOT_FETCHED, not invented.
- ⚠️ GitHub Actions scheduled runs can start late; there is no true intraday signal activation or **actual customer trading ledger**. No broker orders are placed.

**Hard gate:** In the current research-only version, `signals.json` must never contain actionable buy orders. `research_candidates` are not validated trading recommendations.
 
### Validated research-only run (2026-10-28)
- [Run 40683516634](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40683516634) passed **12 deterministic unit tests** and executed real 12-symbol data downloads, 45 daily-bar historical replay trades, and immutable-by-filename Git evidence.
- Across those 12 *ex-post selected* names, historical funnel recorded **110 possible signals**: 62 conditional price triggers, 44 no trigger, 4 gaps above chase ceiling; these are not independent executable portfolio trades.
- Of 45 completed OHLC-proxy trades, 42.22% show positive net return and mean net return is **-0.2769%**; in the most recent six-calendar-month historical partition (12 trades), win rate is **33.33%** and mean trade net return **-0.79889%**.
- These are diagnostic figures from a biased research subset, not future predictions, validated OOS, or a backtest suitable for deploying capital. The current model remains **trade authorization OFF**. 


## Running
Actions: [workflow page](../../actions/workflows/ashare.yml).
Cron (UTC): 00:30, 04:30, 09:30 on weekdays (Beijing 08:30/12:30/17:30). Actual China exchange holidays are checked in Python.

Local: `python -m pip install -r requirements.txt && python -m pytest -q && python runner.py --phase close --out output`

Output artifacts:
- `audit.json`: dependencies, providers, timestamps, failure reasons, replay metadata.
- `signals.json`: real-data research candidates only, with explicitly unverified intraday conditions.
- `historical_trades_exploratory.json`: daily OHLC trade replay with explicit execution proxies.\n- `records/YYYY-MM-DD/{pre,mid,close}/{run_id}-a{attempt}.json`: versioned by unique run id, includes audit, research signals, full trade replay and SHA256 hashes; retained in Git history. Git administrators could rewrite history, so not absolute immutability.

## Source and validation
- [AKShare](https://github.com/akfamily/akshare) — market data APIs.
- [AKQuant](https://github.com/akfamily/akquant) — engine smoke test; full strategy port not yet integrated.
- [QuantStats](https://github.com/ranaroussi/quantstats) — trade-sequence stats (not actual portfolio drawdown).
- BaoStock — independent fallback to live historical series, provider clearly labeled.

All trade calculations require timestamped, authentic data; unit tests and successful dependency installation are necessary but insufficient. There is no automatic order placement.

## Reusable GitHub skill
[skills/github-connector-write-deploy/SKILL.md](skills/github-connector-write-deploy/SKILL.md) describes verified connector permissions, create/update file, GitHub Actions deployment and artifact audit, reusable in other projects.


## Research hypothesis H01: pre-known CSI300 + CSI1000 trend gate (2026-10-28)
- [GitHub Actions success: run 40685553957](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40685553957): **16 deterministic tests passed**, real index and 12 selected stock histories fetched, 45 historical daily-bar execution proxies reconstructed, evidence committed to [audit record](records/2026-10-28/close/40685553957-a1.json).
- H01 frozen before this fresh run: Both CSI300 and CSI1000 above MA20 **and** MA60 at each signal-date close. From already inspected 45 trades, 33 pass (mean cost-adjusted -0.2160%) and 12 reject (mean -0.4444%). **The pass subset still loses**; do not activate H01 as an endorsed strategy. This is retrospective and contaminated, not independent OOS.
- Major exit losses: 13 stop-gap trades average -2.7482%; 66.81% of the sum of absolute losses across all losing trades. The matched same-entry T+3-close benchmark mean is +0.1751%, the original stopped/targeted policy mean -0.2769%. This daily-close proxy benchmark is not an execution claim; it is hypothesis-generating only.
- **Release gate stays CLOSED:** zero actionable signals; must fix point-in-time all-A security universe, real 14:50 fills, validated breadth, costs/limit-down, and new forward paper-trade evidence.
- See [research plan H01-H04](../../issues/2) and [release gate](../../issues/1).
