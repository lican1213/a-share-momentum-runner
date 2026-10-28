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

## 2026-10-28：原始国家队资金指标工程化并停止旧追涨定时计算
- [核心四ETF Python实现](../national_team/core_flow_factors.py)与[真实执行的算术CI](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-factors.yml)；公式验证使用合成fixture，不代表官方ETF份额或净值已被成功抓取。
- 恢复原四只 510300/510310/510330/159919，日度净申赎、5日累计/期初AUM、两种覆盖率、终点NAV差法敏感性；要求份额、NAV、AUM独立发布时间及来源。
- 将旧三日动量Workflow改为手动/代码变更CI，取消旧的每日三次定时执行；其历史数据、H01/H04结果仍保留。用户的ChatGPT三时段报告仍运行，核心改为四ETF资金指标＋国家队公开持仓。
- 国家队专用官方份额、NAV及沪深300流通市值实时抓取仍**未完成**；根据[Issue #3](https://github.com/lican1213/a-share-momentum-runner/issues/3)执行，不得把纯算术单测报告为国家队已被监测到的资金行为。

## 2026-10-28：策略重点确认为“国家队资金信号之后的成分股选择”
- 用户指出核心不是单纯监控国家队，而是**国家队相关资金信号后筛选并跟踪相应股票，争取跟随收益**。
- [ADR-0004](decisions/ADR-0004-stock-selection-after-flow.md) 固定两条身份路径（具体国家队公司持仓与ETF一级市场全体净申赎不能混淆），提出资金份额 × 当时ETF权重→股票潜在敞口/20日成交额，另检验相对沪深300强势。必须对比直接持有ETF，研究5/10/20日扣成本超额收益。
- [EXP-0003](experiments/EXP-0003-etf-to-stock.md)、[stock_selection.py](../national_team/stock_selection.py) 已提交；[实际测试 40693488577](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40693488577)通过**16项合成数据单测**，不代表真实PCF/国家队持仓数据已抓到，更不代表有可盈利股票名单。
- 旧三日追涨不重新激活。要实现后半段需先补官方ETF份额、历史PCF/权重和点时股票20日成交额等真实数据，全部证据可追踪到时点和原始来源。

## 2026-10-28：对抗式审计纠正过度防御的选股门槛
- 用户要求剔除过度防御、过于保守导致无机会的算法。审计证实旧`stock_selection.py`要求四只ETF完整PCF+全部成分股数据齐备，否则停止；固定ADV1亿元、上市250日、相对强度0%～10%也未经检验就作为硬门槛；负向资金直接清空名单。
- 新主研究入口 [opportunity_scan.py](../national_team/opportunity_scan.py) 把机会排序和成交审计分层：核实的部分资金来源可生成带覆盖率的研究名单、缺股票时其余股票继续、负向资金出金也排名、任意未验证阈值仅标注风险。保留旧严格版用于审计/复现。
- [GitHub实际测试](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40697156501) **26项合成数据单元测试全部通过**；此验证是算法的能力，不等于实时国家队选股或获利实验，实际ETF份额/PCF的采集仍待开发。
- 核心方向始终：四ETF入金/出金→成分股增量相对交易容量→5/10/20日成本后相对直接ETF的超额收益。执行订单独立控制，不应限制Agent输出待验证的研究机会。

## 2026-10-28：对抗式P0/P1全链路审计与修复
- 已归档[审计报告](audits/AUD-2026-10-28-red-team.md)。原来仅有合成数据测试；新增[真实交易所份额+NAV数据采集器](../national_team/live_etf_sources.py)与独立Actions，首次[run 40698385410](../records/national_team_etf/2026-10-28/40698385410-a1.json)：沪市三ETF及NAV真实取数、深市159919日频连接重置。禁止拿此输出冒充四ETF完整指标。
- [run 40698907834](../records/national_team_etf/2026-10-28/40698907834-a1.json)确认三沪ETF在2026-10-26→27净申购代理合计5654849760元，另有159919**日期未确定**的最新份额，只可按捕获时间留档。
- [opportunity_scan.py](../national_team/opportunity_scan.py)已将资金向正/向负股分离、补足未映射净流量/权重覆盖与冲突标记，阻止因缺数据把负敞口误判正向买点。
- [forward_evaluation.py](../national_team/forward_evaluation.py)新增S0 ETF vs 股票候选5/10/20日配对净收益、同/次日开盘时间门槛、成熟期与无法成交截断；当前仅算术测试，尚未获得真实PCF事件后的独立样本。
- 原指标新增企业行动/拆分是否核实标记。接下来P0依旧是159919日频、PCF成分股时点数据、官方市值分母及真实选股收益闭环。

## 未来添加新事件的格式
`YYYY-MM-DD HH:mm +08:00 | actor | question | change/why | prior SHA → new SHA | evidence run | results/limitations | linked EXP/ADR/INC | status`

保留所有失败、被否定假设、回滚理由。新Agent必须在交付有实质变化的代码前补记此页；仅生成run账本不等于更新模型知识。
