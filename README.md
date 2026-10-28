# 国家队公开持仓与ETF净申赎追踪研究 | National-team flow research

**2026-10-28 项目主线已纠偏**：用户目标是追踪中央汇金等可核实机构公开持仓与国家队关注ETF的真实份额净申赎，并检验公开信号之后跟随是否有收益。详见[ADR-0003](wiki/decisions/ADR-0003-national-team-pivot.md)与[首要任务 Issue #3](https://github.com/lican1213/a-share-momentum-runner/issues/3)。旧三日动量系统继续作为历史研究分支，**不是国家队交易信号**。尚未部署官方ETF份额管线，不能把旧运行报告当成国家队买卖记录。


## 对抗式审计（2026-10-28）与真实ETF数据
[完整对抗式审计AUD](wiki/audits/AUD-2026-10-28-red-team.md) · [实际官方份额和NAV采集](national_team/live_etf_sources.py) · [真实源数据运行及故障](records/national_team_etf/2026-10-28/40698907834-a1.json) · [5/10/20日配对股票与ETF收益引擎](national_team/forward_evaluation.py)。

当前已拿到三只沪市核心ETF的交易所份额（AKShare标准化）；历史NAV来自东方财富，需要基金管理人公告交叉核对；深市159919历史日频连接异常，最新基金列表份额无交易日，不回填历史。三沪ETF对2026-10-27日净申购金额代理为**56.54849760亿元**，不能归因于中央汇金。完整四ETF、国家队本人交易身份、PCF选股与超额收益仍未验证。

## 机会优先的股票研究扫描（B9）
[opportunity_scan.py](national_team/opportunity_scan.py)：少一份ETF PCF或少几只股票日线时仍可对**真实可验证的部分**排序，公开覆盖比例；净流出同样提示风险。低流动性、短上市年限、较大相对涨幅只作风险标签，不再一刀切。原 [stock_selection.py](national_team/stock_selection.py) 保留为严格审计版本。两者都不直接提交券商订单。

**已验证**：[26项合成数据测试](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40697156501)；ETF/PCF官方数据采集及真实选股收益仍需运行数据测试。

## 交易策略主线：资金入场线索之后选什么股票？
[ADR-0004 选股决策](wiki/decisions/ADR-0004-stock-selection-after-flow.md) · [EXP-0003 ETF基准S0 vs 股票S1/S2](wiki/experiments/EXP-0003-etf-to-stock.md) · [股票映射代码](national_team/stock_selection.py)。

国家队相关ETF净申赎 → 按当时PCF/持仓权重映射至股票潜在配置敞口 → 以股票20日成交额归一、相对强度分层 → 研究同日同成本5/10/20交易日是否跑赢直接买沪深300ETF。资金流不等于国家队本人的真实订单；代码尚未得到官方PCF/真实股票数据支持，**不能给当前买入名单**。

## 核心：原始国家队ETF资金进出指标已经恢复
[最初四只ETF（510300/510310/510330/159919）资金因子、两类市场覆盖率和五日净申赎强度](wiki/data/original-four-etf-indicator.md)。9ETF是扩展观察池，国家队基金持有人披露是低频身份核验。原始入金出金信号与市场风险环境需要**合并使用**，不能将ETF总申赎误认为中央汇金具体账户当日成交。当前仅提交公式和合成数据测试，尚无国家队专用ETF实际取数结果。

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
