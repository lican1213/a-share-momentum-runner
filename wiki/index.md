---
id: MOC-WIKI
type: moc
status: maintained
updated: 2026-10-28
---
# Wiki 总索引（Map of Content）

[返回根MOC](../MOC.md) · [当前简报](compiled/briefing.md) · [维护协议](../KNOWLEDGE.md)

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
- [股票映射源码](../national_team/stock_selection.py)（只有合成数据测试通过，暂无真实策略回报）

## 原始资金指标与国家队身份交叉验证
- [2026-10-27四ETF原始资金进出指标与双市值覆盖率](data/original-four-etf-indicator.md)
- [最新合并决策：ADR-0003](decisions/ADR-0003-national-team-pivot.md)
- [公式代码和单元测试](../national_team/core_flow_factors.py)（尚非真实行情运行）

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
