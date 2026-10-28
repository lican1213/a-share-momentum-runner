# MOC — 国家队资金跟踪与跟随收益研究第二大脑

**Agent starts here.** [操作规则](KNOWLEDGE.md) · [AGENTS入口](AGENTS.md) · [Wiki总索引](wiki/index.md) · [一页当前状态](wiki/compiled/briefing.md)

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
