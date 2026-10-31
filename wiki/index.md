---
id: MOC-WIKI
type: moc
status: maintained
updated: 2026-10-31
---
# Wiki 总索引（Map of Content）

## 2026-10-31 左侧低位跟随研究（计划，尚未实现）
- [EXP-0007完整计划：四ETF资金逆势承接→抗跌未涨个股→F1/F2对照](experiments/EXP-0007-flow-absorption-low-entry-plan.md) · [ADR-0005：回归用户原始四ETF主信号](decisions/ADR-0005-low-entry-research.md)。
- 保留旧A2/B追突破信号做反事实，不能回写原始G1冻结；不把全ETF净申购写成国家队账户逐股买入。新方案没有新代码、模拟成交或净超额证明。

## 2026-10-30 单一当前执行状态（优先于旧三日项目）
- [当前状态与唯一验收Gate](current-status.md) · [源码](../national_team/short_ab_engine.py) · [最新对抗测试](../tests/test_national_team_short_ab_engine.py) · [四P0真实修复](audits/AUD-2026-10-30-short-ab-execution-closure.md)
- [A2盘后首次合法冻结](../records/national_team_short_ab/freezes/A2/2026-10-30.json) · [B盘后首次合法冻结](../records/national_team_short_ab/freezes/B/2026-10-30.json)；G2/G3/G4待成熟、真实券商0笔。


[返回根MOC](../MOC.md) · [当前简报](compiled/briefing.md) · [维护协议](../KNOWLEDGE.md)

## B16真实四ETF→V2独立股票名单与前瞻收益跟踪
- [EXP-0004研究协议与结构限制](experiments/EXP-0004-four-etf-strategy-v2.md) · [正式V2选股代码](../national_team/strategy_v2.py) · [GitHub实际完整运行40719359363](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40719359363)
- [固定两组V2研究股与完整排名原始证据](../records/national_team_strategy/2026-10-28/40719359363-a1-v2.json) · [第一次前瞻冻结事件](../records/national_team_events/2026-10-28/40719359363-a1-v2.json) · [专用自动化](../.github/workflows/national-team-strategy-v2.yml)
- [20日到期覆盖修复](../national_team/live_paper_tracker.py)：保留最近60自然日中至多64个冻结事件，缓存同股票OHLC源；不再让后续两组/天把前八条尚未成熟结果挤掉。
- 研究股单尚非国家队逐股订单；相同中证权重无法用四ETF金额区分股票，只能验证资金事件择时对S1/S2是否有超额收益。

## 最新端到端资金—选股—对抗审计
- [B11/E2E实际运行与红队审计](audits/AUD-2026-10-28-e2e-release-gate.md)
- [实测四ETF资金份额及NAV](../records/national_team_etf/2026-10-28/40702172792-a1.json)
- [多运行无冲突合并7个完整交易日](../records/national_team_merged/2026-10-28/40702572594-a1.json)
- [指数权重代理的30只股票实测研究名单](../records/national_team_watch/2026-10-28/40702172792-a1.json)
- [上交所带超时官方接口](../national_team/sse_direct.py)、[深交所按代码日期JSON](../national_team/szse_json.py)、[数据冲突隔离](../national_team/record_merge.py)
- [纸面事件冻结](../national_team/paper_events.py)、[未来收益评估](../national_team/live_paper_tracker.py)、[原始数据独立重算审计](../national_team/audit_gate.py)
- 官方PCF和国家队法定主体确认、真实前瞻超额收益仍需独立检验。

## 机会优先的研究入口
- [主动选股扫描器](../national_team/opportunity_scan.py)：部分真实篮子/个股数据可形成带覆盖率和风险标签的研究排名，资金流出也追踪；只将已知错误或未来数据拒绝。
- [ADR-0004纠偏说明](decisions/ADR-0004-stock-selection-after-flow.md)：研究机会发现与交易授权分开，历史严格审计器留作复现。

## 本轮对抗审计与真实数据证据
- [AUD-2026-10-28 P0/P1系统审计与修复](audits/AUD-2026-10-28-red-team.md)
- [2026-10-28真实四ETF采集尝试账本](../records/national_team_etf/2026-10-28/40698907834-a1.json)
- [ETF份额/净值真实采集代码](../national_team/live_etf_sources.py)
- [5/10/20日股票与ETF配对收益计算](../national_team/forward_evaluation.py)

## 真正的收益策略（优先跟踪）
- [ADR-0004 ETF资金变化之后选哪些股票](decisions/ADR-0004-stock-selection-after-flow.md)
- [EXP-0003 S0直接ETF vs S1资金冲击选股 vs S2价格确认选股](experiments/EXP-0003-etf-to-stock.md)
- [股票映射源码](../national_team/stock_selection.py)（旧严格研究模块；B11另有真实市场指数权重代理名单，尚无成熟收益）

## 原始资金指标与国家队身份交叉验证
- [2026-10-27四ETF原始资金进出指标与双市值覆盖率](data/original-four-etf-indicator.md)
- [最新合并决策：ADR-0003](decisions/ADR-0003-national-team-pivot.md)
- [公式代码和单元测试](../national_team/core_flow_factors.py)（B11已与真实ETF份额和NAV结合运行）

## 当前最高优先级——国家队资金行为
- [ADR-0003 主线重定向](decisions/ADR-0003-national-team-pivot.md)
- [国家队官方份额与持有人MVP](https://github.com/lican1213/a-share-momentum-runner/issues/3)
- 旧动量实验详见EXP-0001与EXP-0002，作为历史基准存档，不继续主导开发。

## 项目知识
- [研究现状](overview.md)
- [模型版本登记](models/registry.md)
- [数据与回测口径](data/contracts.md)
- [来源目录](sources/catalog.md)
- [未解决的问题](open-questions.md)

## 为什么这么做（决策）
- [ADR-0001 不开放交易指令](decisions/ADR-0001-no-trade.md)
- [ADR-0002 原始证据优先，失败关闭](decisions/ADR-0002-evidence.md)

## 试了什么（实验）
- [EXP-0001 基线结果与出场机制](experiments/EXP-0001-baseline.md)
- [EXP-0002 H01市场趋势门槛](experiments/EXP-0002-regime.md)

## 哪里错过（故障）
- [INC-0001 权限与行情、回撤索引错误](incidents/INC-0001-bootstrapping.md)
- [CTR-0001 错误诊断和矛盾结论的证据](contradictions/CTR-0001.md)

## 何时做的（时间索引）
- [Wiki维护日志](log.md)
- [Actions运行账本索引](indices/runs.md)
- [Git提交时间线](indices/commits.md)

## Agent如何继续
- [操作与交接](operations/handoff.md)
- [实验页模板](templates/experiment.md)
- [决策页模板](templates/decision.md)
