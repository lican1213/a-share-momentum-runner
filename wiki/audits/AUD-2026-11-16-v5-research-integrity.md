---
id: AUD-2026-11-16-V5-INTEGRITY
type: audit
status: active
updated: 2026-11-16
---
# 11月16日：V5研究有效性和真实执行复核

## 生产证据（北京时间）
- 11月13日计划16:20 ETF采集实际次日00:33开始；17:25 V3实际次日01:16开始；随后V5和账户在3—4秒完成触发。见 [源采集](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43463932968)、[V3](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43471137373)、[路由](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43471238140)、[账本](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43478606014)。完成触发有效，根cron仍不合格。
- 最新四ETF交易所原始完整日11/12；11/13只有三只SSE份额。V3使用历史缓存四ETF，不等于同日官方完整确认。原始普通流通市值CSV先前只有表头。
- [11/14账本](../../records/national_team_paper_accounts_v5/2026-11-14/43478606014-a1.json)：24条决策，9笔入场，6条缺OHLC，5条预算风险，3条已满2仓，1条重复持仓。三组均空仓；净盈亏-7.69/-64.01/+37.16元，同本金扣费超额-39.06/-43.23/+6.26元。4个冻结属于同一个10/26簇，不是4个独立事件。
- [前瞻结果](../../records/national_team_left_outcomes_v5/2026-11-14/43478606014-a1.json)后两组事件三臂股票重叠；此现象不能通过强行选择不同股票制造独立性。真实冻结和旧记录全部保留。

## 提交修复及验收
1. 最新真实指数日期显式保留，旧筛选快照缺最新日期时路由等待而非重用旧信号；完整六交易日份额连续性；已有主覆盖率变化时优先原指标，缺失时仍允许已定义份额代理研究。主指标观察标签不伪称历史PIT。
2. 同一股票集合不充当有效左侧比较；完整成熟两臂才用于学习；不改变8独立事件、+0.2个百分点切换条件。保持现有排名，明确重叠而非硬凑对照。
3. 按已有150元风险限额和实际最低佣金整手缩量，不因旧模型估算漏最低佣金直接放弃订单。备用行情补齐真实已观察的漏日，不覆盖已有主源OHLC，保留来源哈希。
4. 不回写任何历史账本/冻结，不授权券商交易，08:30/12:30/17:30检查与原GitHub cron均不减少。

## 未关闭的门
- 代码与新测试需对应PR全量CI验证，合并后新真实归档验证；此文档不是通过证明。
- 持续同日普通流通市值及自由流通市值需要真实数据供给。上交所统计月报证券指数表有普通流通市值（历史延后发布），中证指数每日报告另有自由流通市值列；两者不能互代。Tushare index_dailybasic可提供普通流通市值，接口权限/000300.SH实际返回须验证。不用指数点位反推或猜造。外部可靠调度需要授权调用workflow_dispatch；GitHub cron本身无法由串联修复。不得以新代码代替真实准点验收。

## 第二阶段：真实分母接入和任务编排（等待生产Gate）
- 已验证的PR #12：源码020d671da5d4、[G0真实运行43850165365](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43850165365) **295 passed / Wiki50页PASS**，合并SHA e4a730dfb9aa。不能将这个CI证明当作第二阶段验收。
- 官方[上证统计月报证券指数表](https://star.sse.com.cn/aboutus/publication/monthly/index/)公开的2026-09沪深300流通市值表，已按明确“亿”转为CNY录入8个可核验交易日；原始公布时刻未知，CSV published_at使用本次观察的保守上界，禁止计作历史点时可用。源网页为动态月报，月份和八个原数已在CSV固定，不推断未观察日期。
- [中证指数2026-10-29报告](https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/researches/files/zh_CN/csiindexdailyreport20261029.pdf)列自由流通市值，但页内单位与是否经过靠档调整未充分核实，不把该值当普通流通或未经证实的真实自由流通市值。
- [行情供应商适配器](../../national_team/csi300_cap_sources.py)核对000300沪深300身份、已完成收盘的源时间戳、与独立回放的同期收盘点位一致、f117/f116 CNY及合理量级；成功记录原始响应及哈希，错误显式记录。f117供应商口径不能标为交易所官方值。持续积累只取既有V3不可覆盖记录，不发明前值。
- V3新增已有ETF实际采集成功的workflow_run路径，原cron17:25保留；V5已有完成触发继续用。新链不等于GitHub根cron可靠，需真实重复准点验收；不另起Runner、并保留原三时段ChatGPT检查。数据日期错误、未收盘和缺份额时不把旧事件再作新事件。

## 第三阶段：避免重复OHLC访问与摘要过时
- 第一轮在合并SHA e4a730df真实[账户运行43850315658](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43850315658)完成11/16市场日期推进，三组历史账户余额未漂移、source_errors=[]；新[路由43850455250](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43850455250)返回11/16 WAIT_LATEST_SESSION_EVIDENCE（数据提交SHA 76a424f7），不把11/13旧日冒充新信号。
- 第二轮[PR #13](https://github.com/lican1213/a-share-momentum-runner/pull/13)源码685b7fff，[G0 43850469538](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43850469538) **303 passed / 50页Wiki通过**，合并5bde9a01；生产供应商capture仍需核验。
- V5跟踪原先每个冻结重复请求510300和重叠个股；本次统一为同一批次一次取数、日期范围裁切、独立Sina ETF OHLC备用及股票Baostock。收盘前只取上一已结束日线（特别是新增源完成触发后，禁止当日未完成日K推进T+2）。
- 修复派生Wiki只枚举历史V2/A2的事实：最新V3、V5路由、冻结、前瞻和账本都列入编译简报及索引。原始账本、策略、通知配置均不重写。第三轮G0/G1未完成时不宣称通过。

## 阶段二/三下游复核（用户要求；新PR待G0/G1）
- [第三轮真实账本](../../records/national_team_paper_accounts_v5/2026-11-16/43850945324-a1.json) 与第一轮 43850315658 三组现金、权益、同额S0净超额、各8条决定和各3笔平仓完全相同，市场日均11/16；第三轮[前瞻归档](../../records/national_team_left_outcomes_v5/2026-11-16/43850945324-a1.json)显示新浪原个股接口全体触发AKShare更名错误，东方财富510300限流，Baostock与Sina ETF备用实际恢复；不能只看账本source_errors=[]。
- 修复已确认API改名（新接口优先、旧版兼容；仍不复权）。原始月报8个普通流通市值复核一致。拒绝的实时分母响应后续记录原文hash，不放松日期/来源核验。
- V3必须真实消费最新带时钟的合并交易所四只份额/NAV，按完整篮子覆盖精确日期，冲突/缺失不冒充官方值；外部缓存基准单独保留，11/13官方份额完整但NAV未齐的事实不可写成完整资金因子。历史迟报市值不作为当时可得的主信号；现时观测仍单独区分。此调整可能改变后续候选，不回写历史仓位/现金。
- GitHub官方 [workflow_run三级限制](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run)：ETF→V3→路由→账本为三次完成触发；账本归档后改用既有Wiki workflow_dispatch（显式actions:write权限），不新增第四层workflow_run；保留原全部cron与三时段监测。新调度未经多日实际时效验证。
- 新PR需匹配SHA全库CI+新实际归档；独立8个成熟事件条件、资金门槛与原现金本金不变。实时分母接口、公允自由流通口径仍未关闭。

## 第三阶段真实反例：配对结果回退（新修复待G0/G1）
- PR15源码fd5f70de10ac的[308全库测试](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43851601619)已通过，合并459670b78e41。同SHA生产[跟踪43851757253](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43851757253)证明个股API改名异常已消失，510300仍限流且Sina基准到11/13。
- 逐项对比[第一轮前瞻](../../records/national_team_left_outcomes_v5/2026-11-16/43850315658-a1.json)与[第三轮前瞻](../../records/national_team_left_outcomes_v5/2026-11-16/43850945324-a1.json)全部96条组-股票-期限：PAIRED 48→42，UNMATURED均48，6条变S0_MISSING。均为11/06冻结、600050与601818各三组的5日同日比较。原已归档11/16 510300真实日线 O/H/L/C 4.068/4.075/4.036/4.054；第三轮Sina备援缺该日，不能把配对回退当亏损或重新入场。之前6条同额相对净收益为0.084384293及0.7969725567个百分点，各三组。
- 修复：备援后用已留档、哈希一致、观察时点与实际收盘校验过的精确日期原始OHLC仅补缺口；不覆盖当前已取行情、拒绝档案冲突，追溯源路径与hash；不回填模拟买入。历史独立外部回放仍作为原50%入场研究门槛的基准，交易所补源回放单独观察，不让换数据口径直接切换研究许可。
- 新代码不等于实际恢复，必须验证匹配新SHA的归档重新出现48条配对且6条数值可复核、三组现金/成交不变。实时市值缺口与root cron仍未关闭。最新指数日和最新完整资金日错位时，仍需后续验证新到达合法迟报信号不被过期信号保护误伤；此前真实11/13为净赎回，未证明漏买。 

## Ponytail Full 收敛（2026-11-16）
- PR12/13/14/15/16生产证据均保留；[PR16全库310通过](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43852031615)，合并4d680c8e7444。[真实运行43852184259](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43852184259)及[43852350573](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43852350573)两次恢复48/48 PAIRED/UNMATURED，S0_MISSING=0；600050/601818五日超额恢复为0.084384293/0.7969725567个百分点，三组现金、权益及3笔平仓均未漂移。
- [真实V3](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43851757502)：23日完整交易所份额/22日完整份额及NAV；独立基线32/60、28/60、24/59不变；8日普通覆盖率、0日PIT。f124=0，实时分母仍拒绝。Wiki显式触发43851994486成功。
- 按[原版Ponytail](https://github.com/DietrichGebert/ponytail/blob/main/skills/ponytail/SKILL.md)最小改动：统一单次/多事件行情采集，删除重复分支；保留归档补缺原始供应商与hash，避免反复复用后被当前源误标。三套生产工作流push不再因纯测试文件修改触发行情请求；共享模块已有上游路由触发，不再重复触发账本。全部原cron、workflow_run、手动触发、运行中pytest与全库PR Gate保留。MOC只保留一处当前状态并链接本审计，旧版本可从Git历史查阅。
- 不新建Runner、框架、依赖，不调整资金或选股阈值、不删除历史账本。实时分母、根cron准点及合法迟报事件跨日识别仍为已知待验收项。新变更需匹配SHA的CI和生产证据，不把以前的成功作为本轮成功。

## Git历史设计意图复核
- 有意保留：EXP-0012 的3自然日披露滞后、固定四ETF、50%历史方向准入、8独立簇/0.2个百分点；EXP-0014 的不补入场、已承诺迟到退出、三账户预算；EXP-0015政策不作交易门；EXP-0016原cron兜底、未来日期冻结（含保守next_weekday）；旧A2/B/V2/V4只归档。不得为提高成交频次改写协议。
- [PR17](https://github.com/lican1213/a-share-momentum-runner/pull/17) [312项测试/50页Wiki](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43856078252)通过，合并c5ad88b53059。
- 实际遗漏：PR12最新指数日保护误伤EXP-0012允许的合法迟报（当前日只有指数、前一完整资金日新可得）。统一V3行选择、V5路由、冻结和取价；只在新格式明确最新指数日且当前资金缺失时选择最近完整正向日；最新完整负向日不回搜更老正向日，超过3自然日、已有冻结仍拒绝。独立原归档不改。当前11/13实际净赎回，未证实实际漏买，本次为代码可复现反例。
- 实际遗漏：R_BOUNCE仅部分候选成熟时不应把它当完整组对照；同左侧需要组内全部配对，不改8簇门槛。checkout main的真实源码SHA与触发SHA可能不同，使用现有git获取实际工作树SHA写入V5路由、冻结、账本。新增回归测试和生产读回待本PR验收。
- 已知未关闭：实时普通/自由流通市值来源；根cron准点；连续未来事件验证。本轮不引入新数据商、新Runner、依赖或策略，不动历史账本与每日三次任务。

## 同类开源项目取经及上游生产漏洞（2026-11-16）
- PR18已合并9c0f592ae8，[313项全库测试](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43857810166)通过。历史资产不变。
- 读取 [national-team-etf-flow 的实际刷新工作流](https://github.com/wwww1998/national-team-etf-flow/blob/main/.github/workflows/daily-refresh.yml) 与 [refresh.py](https://github.com/wwww1998/national-team-etf-flow/blob/main/refresh.py)：按交易日缓存与次日发布窗口补采。其早间15分钟轮询不整套复制，仅给现有根工作流新增北京时间07:50工作日补采（UTC前日23:50），保留09:15/16:20及下游原cron、完成触发、ChatGPT三时段。根任务实际延迟单独打印证据，GitHub平台延迟仍不保证消失。
- [Qlib数据采集](https://github.com/microsoft/qlib/blob/main/scripts/data_collector/README.md)分离市场日历与行情。本仓库已有XSHG exchange-calendars，直接复用，使新冻结拟入场为严格晚于真实冻结日的下一交易所交易日。按[上交所2026休市公告](https://www.sse.com.cn/disclosure/dealinstruc/closed/)验证国庆与周末，不回写旧意图，不放开当日开仓。
- [实际股票观察43827324850](../../records/national_team_watch/2026-11-16/43827324850-a1.json)：150只候选、0条有效股票快照，新浪与东财300次旧接口错误；指数亦改名。[同run ETF源](../../records/national_team_etf/2026-11-16/43827324850-a1.json)四只NAV全因旧接口更名失败。复用现有AKShare兼容层，按[实际新NAV源码](https://github.com/akfamily/akshare/blob/main/akshare/fund/fund_em.py)保留日期/单位/参数，不改成功的V3历史NAV接口。真实V3原本NAV四只均成功，不重复重构。无有效同日股观察不允许一次性冻结消耗事件；旧官方资金因子不再映射到较新股行情。
- [DR-EUPHORIA/quant](https://github.com/DR-EUPHORIA/quant)采用动态成分历史与daily_basic；[Tushare index_dailybasic](https://tushare.pro/document/2?doc_id=128)当前明确支持名单未写沪深300；直接盲接000300.SH不是解决办法。更可靠的口径是精确生效日的完整300只成分+同日daily_basic的circ_mv（万元）及free_share（万股）×未复权收盘价；[官方字段](https://tushare.pro/document/2?doc_id=32)须权限。当前同类仓库原始面板目录不可取得，本仓库无法核验授权token，且实际10/30成分权重快照不等于11/16有效成分。先保留已核实的上交所月报历史值及真实NA，不加无法验收的供应商；中证10/29日报自由流通列未见明确非靠档口径，不能拿权重调整市值代替。实时分母仍待具名授权及生产证据。
- 本轮新代码需独立CI、真实ETF/NAV和股票观察归档、下游账本比对、后续自然时段检验。无新增Runner/框架，三账户与历史记录、资金阈值、独立成熟条件不变。 

## 直接普通流通市值及独立时钟（2026-11-16）
- PR19 [317 tests and 50 Wiki pages](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43859687531)通过，合并6d45aabbead9。随后独立算术[run43860360031](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43860360031)因XSHG日历依赖未装而失败，补齐现有exchange-calendars==4.13.1。
- [中证数据市场运行统计日报](https://www.csdata.cn/cmsmc/cgfb/scsj/scyxtjrb/index.html)原表300只沪深300样本股流通市值单位万亿元。逐页视觉核对11/04、05、06、09、10、11、12，数值48.96/48.84/48.43/48.57/48.40/48.43/48.21；原PDF链接及实际观察时钟进CSV，指数收盘4101.34/4113.41/4054.28/4056.11/4059.11/4075.71/4043.93，与[原V3](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43858894606)完全相同。先前八日不改。此批为11/16回溯、非原始首发时刻。报告精度0.01万亿元，舍入区间跨零时仅退回已有份额代理。不把扫描OCR、不明确的自由流通靠档指标或当前时点猜值写入CSV。
- 独立报告补源设计为专门的条件数据采集任务：仅真实新报告、截图核对及同期指数一致才追加该CSV，SHA冲突先重读；该CSV原本已是V3 push路径。原08:30/12:30/17:30只读监控不变。自动化是否启用和真实运行须另行确认。
- [独立宿主补触发脚本](../../scripts/dispatch_national_team_if_late.py) 北京08:05、09:30、16:35查近50个root runs，已有active或同slot成功不重复dispatch，缺失才调用[GitHub官方workflow_dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)；外部安全环境提供GH_TOKEN（本仓库Actions:write），禁止写仓库或对话。实际部署尚无授权的外部宿主及凭据；目前只是待CI与生产验收的代码，不是运行中的外部时钟。日程、三账户和历史全部保持。GitHub排队风险仍存在。

## 续审：权重源缓存、空冻结、独立时钟（2026-11-16）
- PR20已合并9b6c6604d2e1，[主分支全库43861082258](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43861082258)与[独立算术43861082300](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43861082300)成功。真实[V3 43861082339](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43861082339)普通覆盖率15日、PIT0日、交易所完整份额/NAV23日；11/16仍无完整四份额，实时分母f124=0拒绝。[账本43861481050](https://github.com/lican1213/a-share-momentum-runner/actions/runs/43861481050)三组现金29992.31/29935.99/30037.16，各3笔平仓、无持仓，48 PAIRED/48 UNMATURED；路由43861173129 WAIT_LATEST_SESSION_EVIDENCE，独立成熟10日簇0。
- [股票观察43860360085](../../records/national_team_watch/2026-11-16/43860360085-a1.json)CSI权重ReadTimeout。上一份[原权重归档43827324850](../../records/national_team_watch/2026-11-16/43827324850-a1.json)已存300只，权重日期10/30，总权重0.99990，首次实际观察11/16 15:57:36+08:00。参考[Qlib缓存](https://github.com/microsoft/qlib/blob/main/docs/component/data.rst)、[daily_analysis远端失败保留缓存](https://github.com/chenmr0/daily_analysis/blob/main/docs/TUSHARE_STOCK_LIST_GUIDE.md)，只复用原不可覆盖档案、完整300只合理权重和原始hash，保留原时钟及档案hash；35自然日为月度代理最大年龄（新工程取舍，非交易门槛），过期、未来、非CSI源、重复缓存和不完整档均拒绝。该代理不是精确同日成员，更不是ETF PCF或市值分母。仍采集真实同日股价。
- 反例：路由有有效watch，第二次真实OHLC却全失效，freeze仍生成0候选并被永久去重。阻断的是无价格证据的空冻结，而非有真实行情但没有合格股票的合法无单结论。工作流保留已完成router/policy，只有成功freeze才落盘；失败仍显示失败，不回填买入。
- [actions-external-cron](https://github.com/austenstone/actions-external-cron)采用独立时钟API并记录漂移；原独立脚本新增长期active识别，55分钟外报ROOT_ACTIVE_STALLED并非成功，不取消运行、不重复派发。当前无外部宿主/Actions:write凭据，不能声称部署。原cron、三次条件监测不变；新市值补源任务已启用，07:30/18:30，尚无首跑结果。中证指数编制方案区分实际自由流通量和靠档调整股本，未核实自由流通市值精确定义前仍NA。新修复待CI及实际运行。
