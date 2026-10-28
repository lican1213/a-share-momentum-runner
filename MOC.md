# MOC — 国家队资金跟踪与跟随收益研究第二大脑

**Agent starts here.** [操作规则](KNOWLEDGE.md) · [AGENTS入口](AGENTS.md) · [Wiki总索引](wiki/index.md) · [一页当前状态](wiki/compiled/briefing.md)

## B11—B12 当前进展：真实四ETF → 股票候选 → 独立审计

**[E2E审计报告](wiki/audits/AUD-2026-10-28-e2e-release-gate.md)** · [四ETF真实来源](records/national_team_etf/2026-10-28/40702172792-a1.json) · [跨运行完整资金快照](records/national_team_merged/2026-10-28/40702572594-a1.json) · [30只真实股票观察排名](records/national_team_watch/2026-10-28/40702172792-a1.json) · [完整量化CI](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-factors.yml) · [最新源采集Actions](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-live.yml)

**已完成**：四只固定沪深300ETF的交易日份额及NAV、日/5日资金指标、SSE/SZSE相互备份与多run合并、CSI300正式指数权重及实际股票ADV20研究排名、S1/S2候选冻结与5/10/20日纸面评价器、基于真实落盘数据的独立红队重算及篡改失败测试。公开持仓身份与ETF实际PCF尚未贯通；当前股票排名是**指数权重研究代理**，不是国家队逐股订单。独立样本外盈利能力仍未得到验证。

**已完成B12**：[真实综合运行40706300084](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40706300084)已成功生成150只股票研究排名（覆盖CSI300权重83.015%）、2026-10-28三沪ETF最新资金代理、两条冻结S1/S2纸面事件及独立审计留档。**最新10月28日缺159919**，最近完整四ETF为10月27日；双日期保留修复在[81项对抗回归CI 40707718330](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40707718330)通过。完成的旧版运行不能替代新修复的综合生产验证。新[带超时SSE原始接口](national_team/sse_direct.py)已部署。

## 研究纪律纠偏：主动发现机会，不让数据缺口清空研究名单
**[研究主扫描器 opportunity_scan.py](national_team/opportunity_scan.py)**：已核实的部分ETF篮子、个股数据可以继续排序，完整列出覆盖比例与风险标签；资金净流出也产生撤退风险名单。停牌/ST等已明确不可交易者单列。历史上过于严格的[stock_selection.py](national_team/stock_selection.py)保留为全量证据审计版而非唯一研究入口。真正实盘订单另行验证，不阻断研究输出。

## 2026-10-28 对抗式审计结论与真实行情落地
**[P0/P1审计完整报告](wiki/audits/AUD-2026-10-28-red-team.md)** · **[真实ETF数据采集器](national_team/live_etf_sources.py)** · **[真实数据运行日志](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-live.yml)** · **[前瞻配对收益计算](national_team/forward_evaluation.py)**

**阶段结论已由B11更新**：独立深交所按日期JSON接口已取得159919历史份额，四ETF份额/NAV和资金指标已真实计算；但国家队本人持仓核验、ETF真实PCF、成本后独立超额收益仍未完成。以顶部E2E审计和run证据为准。

## P0 策略核心：资金信号后如何选股、是否跑赢买ETF
**[ADR-0004 资金→股票映射与ETF基准](wiki/decisions/ADR-0004-stock-selection-after-flow.md)** · **[EXP-0003 S0 ETF基准 vs S1资金冲击 vs S2相对强度](wiki/experiments/EXP-0003-etf-to-stock.md)** · **[研究代码](national_team/stock_selection.py)**

**国家队资金进出指标是触发器，不是最终交易策略。** 从核心四ETF份额变化和披露持仓出发，按当时PCF/成分权重映射到股票，比较股票20日成交额与相对强度；最关键的盈利证据是公开信号之后5/10/20交易日是否持续跑赢低成本沪深300ETF。股票真实日线与指数权重代理排名已取得，但不能将其称为ETF真实PCF对应买单，也不能据此断言已经跑赢ETF。

## P0 原始四ETF入金/出金指标 + 国家队持仓联合追踪（2026-10-28恢复）
**[原始四ETF资金指标、5日强度及双市值覆盖率](wiki/data/original-four-etf-indicator.md)** · **[指标Python实现](national_team/core_flow_factors.py)** · **[ADR-0003整合决策](wiki/decisions/ADR-0003-national-team-pivot.md)**

原指标固定510300、510310、510330、159919；扩展九ETF作为横向比较，中央汇金等持有人披露用于低频身份确认，大盘状态用于风险过滤。**不能把ETF总净申购算成汇金当日买入。** 原三日追涨仅作旧实验，不是模型中心。

## P0 现行唯一主线（2026-10-28明确纠偏）
**[ADR-0003 国家队跟踪重定向](wiki/decisions/ADR-0003-national-team-pivot.md)** · **[国家队ETF官方数据MVP Issue #3](https://github.com/lican1213/a-share-momentum-runner/issues/3)**

**主要目标：从公开披露确认国家队主体持仓、监测相关ETF的实际份额净申赎，研究在信号首次公开可得之后跟随能否盈利。**

原三日突破策略、45笔历史回放、H01研究全部作为**旧实验/历史证据**保留，不再是主线，停止无目的优化。ETF份额流入只能说明该ETF全市场净申购，不能直接声称中央汇金当天买入。无经核验的真实交易数据则不发可执行指令。

## 1. 当前项目与安全边界
- [当前结论 / 研究架构](wiki/overview.md)
- [模型版本台账及状态](wiki/models/registry.md)
- [当前重大未完成问题](wiki/open-questions.md)
- [发布门槛 Issue #1](https://github.com/lican1213/a-share-momentum-runner/issues/1) · [改善路线 Issue #2](https://github.com/lican1213/a-share-momentum-runner/issues/2)

## 2. 证据与复现
- [运行记录自动索引](wiki/indices/runs.md)（按实际 `records/` 重建）
- [代码提交索引](wiki/indices/commits.md)（按 Git 提交重建）
- [数据口径、时间戳、成交假设](wiki/data/contracts.md)
- [原始逐次运行 JSON](records/) · [GitHub Actions](https://github.com/lican1213/a-share-momentum-runner/actions)
- [数据源 / 项目参考](wiki/sources/catalog.md)

## 3. 研究、升级与失败
- [EXP-0001 原始三日策略与退出归因](wiki/experiments/EXP-0001-baseline.md)
- [EXP-0002 H01 双指数趋势过滤](wiki/experiments/EXP-0002-regime.md)
- [ADR-0001 Research-only 决策](wiki/decisions/ADR-0001-no-trade.md)
- [ADR-0002 数据证据与失败关闭](wiki/decisions/ADR-0002-evidence.md)
- [INC-0001 初次部署、403、接口与QuantStats错误](wiki/incidents/INC-0001-bootstrapping.md)
- [CTR-0001 被证伪的原因诊断与相互矛盾的结论](wiki/contradictions/CTR-0001.md)
- [维护时间日志](wiki/log.md)

## 4. 后续Agent操作
- [交接指南（接手必读）](wiki/operations/handoff.md)
- [MOC/Wiki维护规范](KNOWLEDGE.md)
- [Claude Code入口](CLAUDE.md) · [Gemini CLI入口](GEMINI.md) · [GitHub Copilot入口](.github/copilot-instructions.md)
- [实验模板](wiki/templates/experiment.md) · [决策模板](wiki/templates/decision.md)
- [GitHub连接器部署Skill](skills/github-connector-write-deploy/SKILL.md)
- `python scripts/wiki_lint.py` 与 `python -m pytest -q`

**当次记录可审计 ≠ 模型有效 ≠ 实盘交易已执行。** 最近可核实的研究性运行： [run 40685553957](records/2026-10-28/close/40685553957-a1.json)，16项测试通过；45笔基于真实行情的**假设成交回放**仍为负期望，H01过滤后也仍为负。当前仓库没有任何已授权的可执行买点。
