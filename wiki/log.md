---
id: WIKI-LOG
type: log
status: maintained
updated: 2026-10-28
---
# LLM Wiki维护日志（人工策展，不覆盖旧结论）

> 操作型模型升级变更须在本文件**追加**事件，并在相应主题页归档；与之独立的每次运行快照自动写到 `records/`，全部Git提交历史写到 [commits.md](indices/commits.md)。下列2026-10-28条目为根据Git提交/真实Run的**回溯补录**，不是当时已经建立的Wiki日志。

## 2026-10-28：从空仓库到真实代码执行（回补）
- 目标：从用户原来的口头推荐、在线行情引用，升级为真实代码运算并留证。
- [初始化仓库791919e0](https://github.com/lican1213/a-share-momentum-runner/commit/791919e08565)、[三时段Actions a7c2ef52](https://github.com/lican1213/a-share-momentum-runner/commit/a7c2ef5284de)与 [原始策略8f41d850](https://github.com/lican1213/a-share-momentum-runner/commit/8f41d850e3ce)。
- 过程包括GitHub App 403→授权成功，行情断连，QuantStats整数索引错误被定位并修复。详见 [INC-0001](incidents/INC-0001-bootstrapping.md)。
- **不能推出**模型可盈利、已实际下单或数据覆盖全A。

## 2026-10-28：增设失败关闭与逐笔持久化（回补）
- 将信号分为 `research_candidates` 与 `signals=[]`，任何成功运行也不自动允许建议买入。见 [ADR-0001](decisions/ADR-0001-no-trade.md)。
- 引入T+1、T+3、涨跌停限制的粗略判定，缺失成交须标记censored，时间分割不能自称真正未触碰样本外。见 [数据协议](data/contracts.md)。
- [GitHub自动run留档11ed96a3](https://github.com/lican1213/a-share-momentum-runner/commit/11ed96a3a144)已被后续成功运行证实；逐笔证据在 [run 40683070796](../records/2026-10-28/close/40683070796-a1.json)。

## 2026-10-28：模型负收益与H01观察（回补）
- [EXP-0001](experiments/EXP-0001-baseline.md)：45笔日K代理交易−0.2769%/笔；13笔隔夜跳空止损贡献亏损绝对值的66.81%。
- [EXP-0002](experiments/EXP-0002-regime.md)：指数MA门槛通过组33笔仍平均−0.2160%，不是改进成功；保留先前更差的拒绝组12笔−0.4444%。
- [run 40685553957](../records/2026-10-28/close/40685553957-a1.json) 实际16项测试通过；始终不开放正式交易指令。

## 2026-10-28：引入LLM Wiki / MOC知识治理（本次）
- 新建 [根MOC](../MOC.md) / [Agent规则](../AGENTS.md) / [维护制度](../KNOWLEDGE.md) 与模型台账、实验、ADR、INC、数据、来源和开放问题等页面。
- 借鉴 [Better Second Brain](https://github.com/maystudios/better-second-brain) / [LLM Wiki](https://llmwiki.cc/docs) 的原始证据→维护Wiki→Agent规则结构，明确实时运行JSON不可改写、知识页可追加/修订、generated索引自动重建。
- 本次仅改变文档/持续集成索引，不改模型进出场参数；新CI成功验收前，Wiki自动索引维护为**待验证**。

## 2026-10-28：错误诊断与知识矛盾归档（本次）
- 新建 [CTR-0001](contradictions/CTR-0001.md) 追踪交易日历误诊、QuantStats实际错误、行情来源字段纠正、H01相对改进仍亏损等。旧错误不能在摘要中被静默抹去。

## 未来添加新事件的格式
`YYYY-MM-DD HH:mm +08:00 | actor | question | change/why | prior SHA → new SHA | evidence run | results/limitations | linked EXP/ADR/INC | status`

保留所有失败、被否定假设、回滚理由。新Agent必须在交付有实质变化的代码前补记此页；仅生成run账本不等于更新模型知识。
