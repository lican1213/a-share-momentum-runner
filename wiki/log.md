---
id: WIKI-LOG
type: log
status: maintained
updated: 2026-11-02
---

## 2026-11-02：修复V5纸面盘功能断层，EXP-0014

- 用户指出精简旧A2/B后无法观察真实持续的模拟现金和进退场。源实测：V5首次[路由#41375272862](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41375272862)未生成新冻结，[跟踪#41375272899](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41375272899)只跟踪0事件；原F1候选`fill=None`，并非完整纸面账户。认可遗漏，不复用旧右侧追高策略。
- 在原V5 18:45结果追踪中增加[EXP-0014](experiments/EXP-0014-v5-paper-account.md)：三臂独立虚拟3万元账户，保留真实开盘情景与T+1、单笔150元/总敞口1万元、100股、买卖扣费、预设止盈止损、T+2时间退出、同日510300比较代理；失败和空仓有明示的现金状态。历史账本不覆盖，新快照逐日独立归档。
## 2026-11-02：定时任务跟随V5主线收敛（EXP-0013运维补完）

- 原ChatGPT三时段跟踪仍使用过时V4/A2/B指令；现已保持08:30/12:30/17:30频率不变，替换为从最新MOC/真实Actions证据动态识别EXP-0013资金主指标、SHALLOW_DIP/DEEP_DIP/R_BOUNCE与3/5/10/20日MFE/MAE、510300扣费对照，不复述固定旧run。
- 两个旧A2/B工作流删除push与工作日18:15/20:15/22:15共6次自动启动，仍可按需手动执行历史研究；留旧源码、冻结和账本，EXP-0011 20日旧冻结收益跟踪保持现有计划。V5两条日程不变。
## 2026-11-02：收敛旧执行路线，给V5增加收益路径学习（EXP-0013）

- 单一V5冻结/追踪扩展[EXP-0013](experiments/EXP-0013-path-learning-and-retirement.md)：左侧浅跌/深跌之外新增温和右侧R_BOUNCE影子，未来同源3/5/10/20日MFE/MAE、资金事件S0净超额与Baostock末级个股日线恢复。缺源、不成熟仍NULL，不伪造止盈订单。
- 退役5个旧任务文件并在根MOC记录可永久访问的旧SHA；直播ETF采集器删除旧S1/S2每日冻结与旧纸面跟踪分支，新数据只供V5路由。仍有短期到期需要的A2/B与EXP-0011后验跟踪不删。



## 2026-11-02：落地Super-agent式观察→行动→反馈循环（EXP-0012）

- 无需运行DeepSeek原型：在现有Python/GitHub Actions中增加固定四ETF盘后历史刷新、同日源事件路由、自动独立低位纸面冻结、两组未来OHLC跟踪、8个10日成熟事件后的自适应排序。见[实验合同](experiments/EXP-0012-four-etf-autonomous-event-loop.md)与[事件工作流](../.github/workflows/national-team-event-router-v5.yml)。
- 修复旧V3没有日常cron、旧V4因源push反复读取10/30固定事件的问题；保留手动复现实验，不覆盖旧记录。低位选股新组先排仍跌的股票，旧最高相对强度优先模型保留为历史基线。相关源码SHA及Actions运行ID以实际验证结果再追加，不提前声称赚钱。



## 2026-11-01：用户反对过度防御，完成旧策略和V4逐项源码审查

- [根MOC机会优先原则](../MOC.md)确立：50%以上历史信号允许小仓位纸面左侧试错，优先逆势ETF承接和还没涨的抗跌股；辅助技术条件转成可见标签，禁止为了“确认安全”层层叠加而让机会榜单空仓。[完整专项审查](audits/AUD-2026-11-01-opportunity-first-overdefense.md)明确旧A2/B硬均线+突破+放量/开盘不可低开、旧完整PCF选股缺一个股快照便整次失败是偏右侧或过度全有或全无。
- V4本轮有150/150真实行情、30只低位合格、其中14只近5日仍跌或持平，但“最高相对强度优先”使首只未涨股排第17；头两只600016/600019近5日分别已涨+2.91/+2.55%。认定用户批评有证据。此轮**只更新理念及审查，不改A2/B或V4原冻结**；新版本事前定义未涨优先，再比较同起点510300和N的费用后净超额。

## 2026-11-01：EXP-0011按用户50%可试口径启动独立低位实验

- 添加[EXP-0011前瞻F1/F2同刻S0自动追踪](../national_team/left_entry_outcomes.py)与[工作日盘后任务](../.github/workflows/national-team-left-outcomes-v4.yml)，仅以未来真实OHLC作开盘成交情景，3/5/10/20日未到期收益为空、对照缺数不得视为零；在首次公开完整冻结前不提前生成未来结果。

- 基于实际[V3 31/59五日方向](../records/national_team_v3/2026-11-01/41281158666-a1.json)达52.54%（同状态纯跌市50%；10/20日47.46/41.38），将阈值定义为**小额纸面实验准入**。[EXP-0011](experiments/EXP-0011-fifty-percent-low-left-paper-pilot.md)新增纯F1左侧筛选、F2弱确认接口、股价追高剔除、100股整手/成本风险预算、S0/N/M对照待成熟、真实OHLC源hash与不可覆盖新记录工作流。所有未来成交先填NULL不伪造，10/09历史失效保留，10/26事件未成熟；旧A2/B不修改。
- 当前实现需要观察本次提交后的真实Actions运行结果，代码完成≠已证实证券超额盈利；首个2026-11-02实际交易日尚未来临。

# LLM Wiki维护日志（人工策展，不覆盖旧结论）

- **首轮P1真实源冻成功：** [V4 Actions #41283487731](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41283487731)，[150/150历史股价与30低位候选JSON](../records/national_team_left_entry/2026-11-01/41283487731-a1.json)。F1冻结600016民生银行、600019宝钢股份，10/30昨收试算8823元，未成交；[同SHA全库241项 #41283487764](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41283487764)、[Wiki #41283487760](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41283487760)通过；10/09失败和未成熟标签原样保留。

## 2026-11-01：V3最终同SHA全绿/十月行情可靠留证
- 新增行情双源重试与重叠收盘一致性核验，14天数据新鲜度失败门槛；[实际源码SHA `16828ce8770084295a0da264c28f8964bcf65d61`的V3成功run 41281158666](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41281158666) 在东财断连后自动用腾讯K线补入74日期，保存全部新增收盘/上游响应SHA256，研究结果保持5/10/20日31/59、28/59、24/58，2026-10-09亏损及10-26未到期不被藏起。对应[全库#41281158714](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41281158714) **228 passed/Wiki41页 PASS**、[原四ETF专项#41281158654](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41281158654) **PASS**；[不可覆盖结果](../records/national_team_v3/2026-11-01/41281158666-a1.json)。原用户主指标沪深300实际流通市值分母仍0日；未达到60%或费用后盈利检验。



## 2026-11-01：V3补全十月真实指数价格与低位抄底失效例
- [成功源运行41280867133](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41280867133)、[单独源哈希JSON](../records/national_team_v3/2026-11-01/41280867133-a1.json)：补入东财2026-07-13—10-30共74个沪深300交易日，10个重叠价格通过交叉核验；份额代理逆势申购去重60簇，5/10/20日上涨31/59、28/59、24/58，不达60%。同四ETF完整日期范围的纯市场下跌对照47/94、45/94、36/93。10月9日簇后5日−2.89%、10日−5.29%；10月26日簇截至10月30日未成熟。不能把成功申购等同止跌成功，更无F1/F2成本后超额。
- 原市值覆盖率2021—2026-10-30的份额+NAV可对齐1262日，但真正同日期沪深300普通流通市值仍未取得，严格覆盖率0天。新增分母晚发布、NAV晚发布、实时增量价格重叠冲突单测；旧冻结未改。新一轮代码验证必须以其对应SHA为准。



## 2026-11-01：EXP-0010第二轮源实跑+同样本对照
- [真实成功V3 Actions 41280606518](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41280606518)、[不可覆盖事件JSON](../records/national_team_v3/2026-11-01/41280606518-a1.json)，源码SHA `c6527b07469b74a0b24ff6b8e587341e1f393323`。1262个四ETF完整份额日、1188个四ETF历史NAV+指数日期；主覆盖率缺沪深300真正的每日市值分母为NULL，不冒充股东持仓。严格10交易日去重，代理5/10/20日上涨30/54、27/54、24/54，同数据日期纯下跌对照46/88、44/87、35/87。2022下跌年份5日5/14；10/20日也5/14。仍无60%稳定胜率及选股净超额。
- 另修复了旧日报两处以10/28固定排名顺序代替当前实际首次冻结文件的脆弱测试；现在按真实归档首次公开名单/同组成员核验，不更改任何旧冻结果或策略参数。最新全库CI须与最终代码SHA匹配。

## 2026-11-01：EXP-0010 V3原四ETF真实覆盖率模型和历史可复算引擎落仓
- 实现[每日四ETF市值覆盖率、下跌期持续增份额与净申购事件](../national_team/coverage_v3.py)，[公开源+SHA256回放CLI](../scripts/replay_national_team_v3.py)，[独立ETF缺数/分母晚发布/份额拆并/去重/收益未到期等反例](../tests/test_national_team_coverage_v3.py)，以及[GitHub Actions自动抓源并追加记录](../.github/workflows/national-team-v3-replay.yml)。旧10/30 A2/B冻结及旧records不修改。
- [EXP-0010完整预注册和验收](experiments/EXP-0010-v3-four-etf-coverage-replay.md)冻结原主指标优先级，20日/5日/10日严格T+2观察，原比值和份额代理两条报告不混淆，年度及市场下跌对照。新代码实际CI与公开历史源run尚须新SHA验证，历史市值分母CSV只给真实来源字段契约、**不添加虚构市值**。输出第一版依旧属于回溯研究，非已验证60%选股净胜率。


## 2026-11-01：用户恢复“ETF市值占流通市值”主指标，独立历史复盘检验60%（源证据与失败保留）
- 用户明确 **头部沪深300ETF市值／沪深300流通市值** 是其最初判断疑似国家队入金出金的第一指标。新增[ADR-0006](decisions/ADR-0006-coverage-ratio-primary.md)纠正上一轮以净申购为首的顺序：覆盖率水平/趋势为主、净份额×NAV解释新增资金，双分母分开，指数调整足迹代理不得冒名真实比值。
- 真实[10月历史事件台账EXP-0008](experiments/EXP-0008-original-coverage-ratio-and-october-flow-event-ledger.md)：逐项读取原四ETF 2026-10-31归档份额NAV并与10月沪深300收盘对齐。10/15—10/29连续11个正申购代理日，7个指数下跌日（10/15、20、21、22、26、27、29）；11日累计+1371.23亿，同期指数-4.17%、四ETF估算AUM+1260.68亿，价格重估-110.55亿。10/30 SZSE份额缺失只作三ETF附注；真实2026-10流通市值分母未得到。
- **真实跑过历史交叉检验**：[EXP-0009](experiments/EXP-0009-four-etf-share-proxy-60pct-historical-pilot.md)，复用GitHub开源1262日期四ETF份额与5164条腾讯CSI300收盘；交集1156完整点时窗口，53去重资金事件：T+2收盘至后5日30/53=56.6%，至10日26/53=49.1%，单纯下跌对照5/10日53.5%/50.0%，没有稳定60%及10日优势。**本次是shares-only代理、回溯公布历史缓存、指数方向标签；未实现原覆盖率真分母与F1/F2净超额**，决不说回测盈利。
- 保留已冻结2026-10-30 A2/B JSON和旧实验、记录、代码不变。本轮新增研究文件和导航日志，非交易代码部署；待真实新SHA Wiki CI通过后方可称文档完整性通过。


## 2026-10-31：用户纠正“买突破股”与原始国家队入金跟随目标（仅计划归档）
- 用户强调最初固定四沪深300ETF份额×NAV就是疑似国家队进场的核心代理，希望在指数仍下跌时借大机构逆势承接尽早参与，而不是10/30中远海控、兴业银行已经上涨后追高。明确ETF净申购为所有持有人总量，国家队法人只在合法披露时确认，保留因子不调参。
- 新增[EXP-0007低位跟随预注册计划](experiments/EXP-0007-flow-absorption-low-entry-plan.md)与[ADR-0005研究决策](decisions/ADR-0005-low-entry-research.md)，借鉴并批判性对照7个GitHub项目；提出下跌×正资金事件、抗跌尚未涨股票、F1左侧/F2弱企稳、ETF与普通抗跌股及旧A2/B四组对照、10日费用后净超额、12类红队反例。
- **本轮只有文档变更**，计划基线main f2fa05587ccd3dfe6f9fb1a73fe8b2bfd6e73d33；未改程序/模型参数/自动化/2026-10-30冻结/旧records，未运行新纸面买入，不能声称验证通过。真正代码开发需重新冻结新commit并通过真实CI与前瞻D1—D4。

## 2026-10-30：第二轮独立反例纠正上一轮“206项已完成”的表述
- 独立审计附录原HEAD`88dfa97dac20`上5条新反例全部失败：历史入场未知、部分资金事件跨日重复、恢复选择第二只S1、14:50强制退出读取未来区间、V2缺失股票作为现金创造虚假正超额。旧206项PASS是事实，覆盖率并不充分。
- [红队审计与修复状态](audits/AUD-2026-10-30-round2-independent-redteam.md)：新分支有不可回写入场判断、全经济事件臂去重、14:50标注及V2未知禁算，保留两份2026-10-30历史完整G1。
- 仍须新SHA全库CI、新红队反例转绿和原记录不改写才可重新标识G0；G2/G3/G4独立于软件验收。

---
id: WIKI-LOG
type: log
status: maintained
updated: 2026-10-30
---
# LLM Wiki维护日志（人工策展，不覆盖旧结论）

## 2026-10-30：P0反例驱动修复与首个真实盘后G1
- 接受审计任务书指出的四项执行缺陷：未知数据曾被误冻、1分钟空洞未检出、T+1/2的14:50以后尾盘漏算、独立冻结事件重复分配资金。逐项新增必须失败反例后修复执行引擎与持久化账本；选股/仓位参数和原V2十股排序均保持不变。
- [A2实际run 41044087760](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044087760)、[B实际run 41044087791](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044087791)于北京时间18:54各用`40640bb97e4b`完成10/10真实源盘后冻结；原件各自归档。G1成功不等于11月2日模拟开盘或未来利润。后续引擎代码修复的验收见[唯一状态页](current-status.md)。


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

## 2026-10-28：真实数据源口径最后校正
- 已确认原始ETF份额来自交易所接口，**历史NAV来自东方财富抓取，并非基金管理人官方一手净值公告**；已在[审计报告](audits/AUD-2026-10-28-red-team.md)中明确需对照基金管理人官方净值/拆并信息。部分三沪ETF流量56.55亿元是研究代理，不升级为一手确认国家队增持。

## 2026-10-28：B11—B12国家队资金—股票端到端开发与独立红队审计
- [E2E完整审计](audits/AUD-2026-10-28-e2e-release-gate.md)。新增深交所官方按代码日期JSON（正确“万份”转“份”）、上交所原始接口带超时与日期字段审计、真实ETF/NAV源与指数成分股票行情统一账本；拆分和第三方NAV尚需复核。
- [真实run 40702172792](../records/national_team_etf/2026-10-28/40702172792-a1.json)：四ETF连续七交易日份额/NAV完整，2026-10-27份额净变化×NAV合计+5612203530元；[30股指数代理实际排名](../records/national_team_watch/2026-10-28/40702172792-a1.json)。此数据不是国家队本人逐股成交，也不是历史当时可得的策略信号。
- [跨运行无冲突账本run 40702572594](../records/national_team_merged/2026-10-28/40702572594-a1.json)：6份来源、0冲突、7天完整四ETF；保留第一观察时间，未把历史回溯数据倒填成历史时点已知。
- 新增 [原始资金独立红队重算](../national_team/audit_gate.py)、[S1/S2研究事件冻结](../national_team/paper_events.py)、[未来收益纸面追踪](../national_team/live_paper_tracker.py)和测试故意篡改/错日期/重复事件。审计以[实际CI 40704384352](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40704384352)的74项通过为**当时版本**证据。其后SSE直接源适配器和其他测试增加，最新版应以其对应Actions输出验收，不能借旧绿色CI背书。
- 实际PCF官方页面HTML暂未提供可解析的日期和全量篮子；保留“指数权重代理”降级标签。未经验证的国家队主体持股和真正的5/10/20日独立净超额收益不标成已完成。
- 生产可靠性修复：SSE直连原接口设明确HTTPS超时/重试，避免AKShare无超时阻断调度；最新150股池和红队自动执行须查最新Actions的完成状态。

## 2026-10-28：B12 最新150只真实股票运行与双时点反例修复
- [实际生产run 40706300084](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40706300084)已完成，150只真实股票的成交额与相对强度、正式CSI300权重代理覆盖83.015%、S1/S2两条冻结研究名单和未成熟纸面收益、红队审计PARTIAL通过均有原始JSON。
- 原新旧项目的关键矛盾被抓出：2026-10-28仅3只沪市ETF可得、2026-10-27仍有7个交易日完整四ETF。修复保留10-27完整因子及10-28三沪ETF净申购+1670914440元作为**不同交易日的两条序列**，不可混用。[真实证据反例回归40707718330](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40707718330)：81项通过，包含金额/日期篡改失败测试。
- [真实数据冻结→红队复现run 40707145019](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40707145019)2项通过，不是盈利证明。最新模型修复后还须看整条生产Actions的同代码SHA和资金审计状态。

## 2026-10-28 B14：从失败运行到完整验收及重大汇金持仓一致性反证
- [运行40710985962](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40710985962) 的真实150股数据采集、模型独立红队与永久`records/`写回都成功。失败原因曾是工作流频繁取消与Wiki动态文件/未暂存文件导致rebase冲突，已拆成两个独立任务；`git restore wiki/indices wiki/compiled`后再提交原始证据。
- [统一决策简报](compiled/national_team_daily.md)（本页位于wiki/，相对链接为`compiled/national_team_daily.md`）：一份文件展示10月27日完整四ETF+56.12亿元、10月28日三沪ETF+16.71亿元和真实150股票S1/S2观察。事前首次可得时点与回测未成熟状态仍清晰。
- [2026-06-30整只159919份额](../data/national_team_holders/159919-2026H1-fund-total.json)：69.39216676亿份，远低于2025年两汇金法人合计354.98494985亿份。历史持仓不能继续当现在仓位；红队标不一致性，尚不能识别具体谁在何日减持。原报告参考[2026年中期报告](https://static.cninfo.com.cn/finalpage/2026-08-31/1225528257.PDF)。
- [源数据报告B14](../records/national_team_daily/2026-10-28/40710985962-a1-v4.json)附当轮审计状态、来源与当时股票名单；旧v1/v2/v3版本不覆盖。
- 尚需ETF真实PCF、2026汇金法人当期持仓、样本外真实股票ETF配对收益来决定盈利Gate，而不是继续增加无证据因子。

## 未来添加新事件的格式
`YYYY-MM-DD HH:mm +08:00 | actor | question | change/why | prior SHA → new SHA | evidence run | results/limitations | linked EXP/ADR/INC | status`

保留所有失败、被否定假设、回滚理由。新Agent必须在交付有实质变化的代码前补记此页；仅生成run账本不等于更新模型知识。

## 2026-10-28：B16（EXP-0004）真实四ETF信号驱动V2独立选股
- [策略正式运行40719359363](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40719359363)成功：基金份额交易日2026-10-27，完整四ETF净申赎代理+56.12亿元；数据首次已知之后在2026-10-28 23:46冻结S1/S2，使用当日150只真实股票成交额与相对沪深300强度。
- [V2源码](../national_team/strategy_v2.py)、[研究协议](experiments/EXP-0004-four-etf-strategy-v2.md)、[真实策略留档](../records/national_team_strategy/2026-10-28/40719359363-a1-v2.json)和[两条冻结事件](../records/national_team_events/2026-10-28/40719359363-a1-v2.json)可独立核验。完成18项策略+回报评价单测及真实历史记录重放，首次生产Git写回成功；随后修复无新四ETF/过期数据分支的Schema，避免未来无信号日误报流程故障。
- 发现旧S2从S1前10股中再次排序、且未严格应用预注册0%—10%相对强度区间，已由独立全池筛选替代；V1旧冻结仍保留，不重写历史。
- **核心反事实缺口**：同一CSI300权重导致资金净申赎为S1横截面打分的公共乘数，触发日期而不决定横截面差异；无法直接证明具体国家队机构买入S1/S2股票。PCF及未来5/10/20日对ETF基准净超额收益尚未成熟，禁止把模型成功运行写成策略已盈利。

## 2026-10-28：V2收益到期追踪的容量缺陷修复
- 发现旧 [paper tracker](../national_team/live_paper_tracker.py) 每次默认只评估最新8个事件。若每交易日冻结S1/S2各1个，事件5/10/20日未到期就会被排除，导致最终无法证实相对ETF的5/10/20日净超额收益。
- 修复为近60自然日、至多64个去重事件；同次运行对同一股票/ETF历史行情仅拉取一次，降低源请求量。工作流 [national-team-live.yml](../.github/workflows/national-team-live.yml) 改为64个事件；合成压力回归[测试](../tests/test_national_team_paper_window.py)覆盖12个事件全部到期、行情重复请求与超期清理。
- 最新资金因子与个股价格的原始观察时间、未来5/10/20期内T+1可行性和真实滑点仍需后续交易日证据。修复只保证追踪覆盖，不是盈利证据。

## 2026-10-30：P0反例驱动修复与首个真实盘后G1
- 接受审计任务书指出的四项执行缺陷：未知数据曾被误冻、1分钟空洞未检出、T+1/2的14:50以后尾盘漏算、独立冻结事件重复分配资金。逐项新增必须失败反例后修复执行引擎与持久化账本；选股/仓位参数和原V2十股排序均保持不变。
- [A2实际run 41044087760](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044087760)、[B实际run 41044087791](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044087791)于北京时间18:54各用`40640bb97e4b`完成10/10真实源盘后冻结；原件各自归档。G1成功不等于11月2日模拟开盘或未来利润。后续引擎代码修复的验收见[唯一状态页](current-status.md)。


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

## 2026-10-28：真实数据源口径最后校正
- 已确认原始ETF份额来自交易所接口，**历史NAV来自东方财富抓取，并非基金管理人官方一手净值公告**；已在[审计报告](audits/AUD-2026-10-28-red-team.md)中明确需对照基金管理人官方净值/拆并信息。部分三沪ETF流量56.55亿元是研究代理，不升级为一手确认国家队增持。

## 2026-10-28：B11—B12国家队资金—股票端到端开发与独立红队审计
- [E2E完整审计](audits/AUD-2026-10-28-e2e-release-gate.md)。新增深交所官方按代码日期JSON（正确“万份”转“份”）、上交所原始接口带超时与日期字段审计、真实ETF/NAV源与指数成分股票行情统一账本；拆分和第三方NAV尚需复核。
- [真实run 40702172792](../records/national_team_etf/2026-10-28/40702172792-a1.json)：四ETF连续七交易日份额/NAV完整，2026-10-27份额净变化×NAV合计+5612203530元；[30股指数代理实际排名](../records/national_team_watch/2026-10-28/40702172792-a1.json)。此数据不是国家队本人逐股成交，也不是历史当时可得的策略信号。
- [跨运行无冲突账本run 40702572594](../records/national_team_merged/2026-10-28/40702572594-a1.json)：6份来源、0冲突、7天完整四ETF；保留第一观察时间，未把历史回溯数据倒填成历史时点已知。
- 新增 [原始资金独立红队重算](../national_team/audit_gate.py)、[S1/S2研究事件冻结](../national_team/paper_events.py)、[未来收益纸面追踪](../national_team/live_paper_tracker.py)和测试故意篡改/错日期/重复事件。审计以[实际CI 40704384352](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40704384352)的74项通过为**当时版本**证据。其后SSE直接源适配器和其他测试增加，最新版应以其对应Actions输出验收，不能借旧绿色CI背书。
- 实际PCF官方页面HTML暂未提供可解析的日期和全量篮子；保留“指数权重代理”降级标签。未经验证的国家队主体持股和真正的5/10/20日独立净超额收益不标成已完成。
- 生产可靠性修复：SSE直连原接口设明确HTTPS超时/重试，避免AKShare无超时阻断调度；最新150股池和红队自动执行须查最新Actions的完成状态。

## 2026-10-28：B12 最新150只真实股票运行与双时点反例修复
- [实际生产run 40706300084](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40706300084)已完成，150只真实股票的成交额与相对强度、正式CSI300权重代理覆盖83.015%、S1/S2两条冻结研究名单和未成熟纸面收益、红队审计PARTIAL通过均有原始JSON。
- 原新旧项目的关键矛盾被抓出：2026-10-28仅3只沪市ETF可得、2026-10-27仍有7个交易日完整四ETF。修复保留10-27完整因子及10-28三沪ETF净申购+1670914440元作为**不同交易日的两条序列**，不可混用。[真实证据反例回归40707718330](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40707718330)：81项通过，包含金额/日期篡改失败测试。
- [真实数据冻结→红队复现run 40707145019](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40707145019)2项通过，不是盈利证明。最新模型修复后还须看整条生产Actions的同代码SHA和资金审计状态。

## 2026-10-28 B14：从失败运行到完整验收及重大汇金持仓一致性反证
- [运行40710985962](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40710985962) 的真实150股数据采集、模型独立红队与永久`records/`写回都成功。失败原因曾是工作流频繁取消与Wiki动态文件/未暂存文件导致rebase冲突，已拆成两个独立任务；`git restore wiki/indices wiki/compiled`后再提交原始证据。
- [统一决策简报](compiled/national_team_daily.md)（本页位于wiki/，相对链接为`compiled/national_team_daily.md`）：一份文件展示10月27日完整四ETF+56.12亿元、10月28日三沪ETF+16.71亿元和真实150股票S1/S2观察。事前首次可得时点与回测未成熟状态仍清晰。
- [2026-06-30整只159919份额](../data/national_team_holders/159919-2026H1-fund-total.json)：69.39216676亿份，远低于2025年两汇金法人合计354.98494985亿份。历史持仓不能继续当现在仓位；红队标不一致性，尚不能识别具体谁在何日减持。原报告参考[2026年中期报告](https://static.cninfo.com.cn/finalpage/2026-08-31/1225528257.PDF)。
- [源数据报告B14](../records/national_team_daily/2026-10-28/40710985962-a1-v4.json)附当轮审计状态、来源与当时股票名单；旧v1/v2/v3版本不覆盖。
- 尚需ETF真实PCF、2026汇金法人当期持仓、样本外真实股票ETF配对收益来决定盈利Gate，而不是继续增加无证据因子。

## 未来添加新事件的格式
`YYYY-MM-DD HH:mm +08:00 | actor | question | change/why | prior SHA → new SHA | evidence run | results/limitations | linked EXP/ADR/INC | status`

保留所有失败、被否定假设、回滚理由。新Agent必须在交付有实质变化的代码前补记此页；仅生成run账本不等于更新模型知识。

## 2026-10-28：B16（EXP-0004）真实四ETF信号驱动V2独立选股
- [策略正式运行40719359363](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40719359363)成功：基金份额交易日2026-10-27，完整四ETF净申赎代理+56.12亿元；数据首次已知之后在2026-10-28 23:46冻结S1/S2，使用当日150只真实股票成交额与相对沪深300强度。
- [V2源码](../national_team/strategy_v2.py)、[研究协议](experiments/EXP-0004-four-etf-strategy-v2.md)、[真实策略留档](../records/national_team_strategy/2026-10-28/40719359363-a1-v2.json)和[两条冻结事件](../records/national_team_events/2026-10-28/40719359363-a1-v2.json)可独立核验。完成18项策略+回报评价单测及真实历史记录重放，首次生产Git写回成功；随后修复无新四ETF/过期数据分支的Schema，避免未来无信号日误报流程故障。
- 发现旧S2从S1前10股中再次排序、且未严格应用预注册0%—10%相对强度区间，已由独立全池筛选替代；V1旧冻结仍保留，不重写历史。
- **核心反事实缺口**：同一CSI300权重导致资金净申赎为S1横截面打分的公共乘数，触发日期而不决定横截面差异；无法直接证明具体国家队机构买入S1/S2股票。PCF及未来5/10/20日对ETF基准净超额收益尚未成熟，禁止把模型成功运行写成策略已盈利。

## 2026-10-28：V2收益到期追踪的容量缺陷修复
- 发现旧 [paper tracker](../national_team/live_paper_tracker.py) 每次默认只评估最新8个事件。若每交易日冻结S1/S2各1个，事件5/10/20日未到期就会被排除，导致最终无法证实相对ETF的5/10/20日净超额收益。
- 修复为近60自然日、至多64个去重事件；同次运行对同一股票/ETF历史行情仅拉取一次，降低源请求量。工作流 [national-team-live.yml](../.github/workflows/national-team-live.yml) 改为64个事件；合成压力回归[测试](../tests/test_national_team_paper_window.py)覆盖12个事件全部到期、行情重复请求与超期清理。
- 最新资金因子与个股价格的原始观察时间、未来5/10/20期内T+1可行性和真实滑点仍需后续交易日证据。修复只保证追踪覆盖，不是盈利证据。
