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

## 2026-10-28：MOC自动维护与跨Agent接入通过真实CI（本次补记）
- [Wiki校验 run 40688051721](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40688051721)：19个Wiki页面ID唯一，所有内部链接存在，Python维护脚本语法检查成功。
- [行情与Wiki同步 run 40687425222](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40687425222)：20项确定性单测、真实数据执行成功、`WIKI_SYNC_OK records=13 views=3`，自动生成 `wiki/indices/runs.md`、`wiki/indices/commits.md`、`wiki/compiled/briefing.md` 并提交Git。
- 新增Claude/Gemini/Copilot入口均指向AGENTS/MOC，避免多Agent指令漂移。
- **界限**：LLM Wiki文档会被Agent依协议维护；自动脚本仅刷新**结构化可验证的运行事实和Git索引**，不会自动生成或擅自修改科学结论。**交易授权继续OFF。**

## 2026-10-28：用户纠正项目主目标——转向国家队资金跟踪
- 用户明确要求跟踪国家队建仓及跟随后的实际收益，而非持续构建通用三日追涨系统。
- 已确立[ADR-0003](decisions/ADR-0003-national-team-pivot.md)与[Issue #3](https://github.com/lican1213/a-share-momentum-runner/issues/3)为P0；旧三日动量研究保持原文件、记录与错误日志，不清理过去证据。
- 研究数据先做ETF官方清算总份额与基金定期报告持有人，不以ETF净申购直接断言某国家队账户买入。尚未执行新国家队数据管线，故不能称国家队策略已跑通。

## 2026-10-28：找回用户原始资金进出指标（源规范纠偏）
- 从2026-10-27原始实施方案找回固定四ETF（510300、510310、510330、159919）的核心指标：ETF_AUM、普通流通覆盖率、自由流通覆盖率、日度Δ份额×NAV、5交易日净申赎/期初规模、3%待检验警报。
- [原始指标合同](data/original-four-etf-indicator.md)恢复两份原始方案间不同的5日NAV计价方法：逐日求和为主、期末NAV终点差法为敏感性对照；不能混合指标口径。
- [代码实现](../national_team/core_flow_factors.py)与[合成数据测试](../tests/test_national_team_factors.py)验证算术和发布时间门槛，不代表ETF官方取数已完成；9ETF与国家队持仓确认作为扩展交叉验证，旧三日追涨保留历史证据。
- [ADR-0003](decisions/ADR-0003-national-team-pivot.md)已补充最初设计而非替代指标。

## 未来添加新事件的格式
`YYYY-MM-DD HH:mm +08:00 | actor | question | change/why | prior SHA → new SHA | evidence run | results/limitations | linked EXP/ADR/INC | status`

保留所有失败、被否定假设、回滚理由。新Agent必须在交付有实质变化的代码前补记此页；仅生成run账本不等于更新模型知识。
