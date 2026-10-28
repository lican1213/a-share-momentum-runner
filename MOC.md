# MOC — A股三日追涨量化研究第二大脑

**Agent starts here.** [操作规则](KNOWLEDGE.md) · [AGENTS入口](AGENTS.md) · [Wiki总索引](wiki/index.md) · [一页当前状态](wiki/compiled/briefing.md)

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
- [实验模板](wiki/templates/experiment.md) · [决策模板](wiki/templates/decision.md)
- [GitHub连接器部署Skill](skills/github-connector-write-deploy/SKILL.md)
- `python scripts/wiki_lint.py` 与 `python -m pytest -q`

**当次记录可审计 ≠ 模型有效 ≠ 实盘交易已执行。** 最近可核实的研究性运行： [run 40685553957](records/2026-10-28/close/40685553957-a1.json)，16项测试通过；45笔基于真实行情的**假设成交回放**仍为负期望，H01过滤后也仍为负。当前仓库没有任何已授权的可执行买点。
