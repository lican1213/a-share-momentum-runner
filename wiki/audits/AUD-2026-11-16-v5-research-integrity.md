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
