---
id: MODEL-REGISTRY
type: model-registry
status: maintained
updated: 2026-10-28
---
# 模型及执行器版本登记（唯一有效升级台账）

**版本必须定义为 Git commit SHA + 实验ID + 运行记录ID。** Git提交时间线由 [commits.md](../indices/commits.md) 生成；本页归纳语义版本，不以“v2表现更好”替代实跑证据。

| 逻辑阶段 | 代表提交 | 主要变化 | 可核验运行 / 状态 |
| --- | --- | --- | --- |
| B0 初始化 | [8f41d850](https://github.com/lican1213/a-share-momentum-runner/commit/8f41d850e3ce) | 原始三日突破策略与日线回放，T+1、T+3、手续费代理 | 尚未成熟，历史初版失败见 [INC-0001](../incidents/INC-0001-bootstrapping.md) |
| B1 数据连接 | [ab6ce8a3](https://github.com/lican1213/a-share-momentum-runner/commit/ab6ce8a3d1ba) | 新浪备用交易日历/数据源、固定观察池；BaoStock后续追加 | 不能据此声称全市场检验 |
| B2 计算修复 | [7234c871](https://github.com/lican1213/a-share-momentum-runner/commit/7234c871b03c) | QuantStats `DatetimeIndex` 回撤修复 | [成功运行40681563446](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40681563446) |
| B3 禁止实盘信号 | [6a377585](https://github.com/lican1213/a-share-momentum-runner/commit/6a37758538a8) | 将 `research_candidates` 与 `signals=[]` 分离，明确只做研究 | [ADR-0001](../decisions/ADR-0001-no-trade.md) |
| B4 回测边界及账本 | [11ed96a3](https://github.com/lican1213/a-share-momentum-runner/commit/11ed96a3a144), [958d142b](https://github.com/lican1213/a-share-momentum-runner/commit/958d142b4e32), [cfc8c4c6](https://github.com/lican1213/a-share-momentum-runner/commit/cfc8c4c645d9) | 限价涨跌停代理、不可成交审查、Horizon分割、逐笔JSON和哈希、Git留档 | [运行40683070796](../../records/2026-10-28/close/40683070796-a1.json) |
| B5 退出归因 / 市场条件 | [3ab42308](https://github.com/lican1213/a-share-momentum-runner/commit/3ab4230818bc) | 退出诊断、H01双指数MA条件、16项测试 | [运行40685553957](../../records/2026-10-28/close/40685553957-a1.json)；H01通过组仍亏损 |
| B6 LLM Wiki 知识治理 | [MOC commit 6ea4826a](https://github.com/lican1213/a-share-momentum-runner/commit/6ea4826a6ae2)、[自动同步CI commit ea6039b8](https://github.com/lican1213/a-share-momentum-runner/commit/ea6039b8b75a) | Agent多端入口、模型/实验/决策/事故Wiki、运行和提交索引自动更新，**不改变交易策略** | [Wiki验证40688051721](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40688051721)19页/无断链；[全量运行40687425222](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40687425222)20项单测且自动索引13条记录已通过 |

## 当前研究标识
- **策略代码**：`strategy.py` 中的三日突破和交易规则，逻辑版本与证据运行的代码 SHA 绑定，不独立宣称“v0.2盈利”。
- **执行器标签**：`runner.py` 当前可能仍报告 `daily-bar research runner v0.1`；该文本不能替代 GitSHA，也不意味着整个仓库停留在最初版本。
- **可执行交易开关**：始终 **OFF / `RESEARCH_ONLY_NOT_TRADE_AUTHORIZED`**。
- **最近已检验实验**：[EXP-0001](../experiments/EXP-0001-baseline.md) 和 [EXP-0002](../experiments/EXP-0002-regime.md)。

## 每次升级必须补全
`version_id`、`parent_sha`、`commit_sha`、`experiment_id`、`decision_id`、规则/数据具体差异、训练范围与不可再用作盲测的历史范围、定量评价指标、CI运行ID、逐笔证据、风险门槛、回滚策略、已观察结果及未完成项。

成功修BUG是**计算正确性提升**；亏损率改善要另有独立交易绩效证据。任何Agent不准把二者混写。
