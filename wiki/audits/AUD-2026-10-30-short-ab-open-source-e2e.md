---
id: AUD-20261030-SHORT-AB
type: audit
status: ci-green-market-freeze-pending
created: 2026-10-30
updated: 2026-10-30
---

# A2/B短线纸面模拟：开源实现对照、失败复现和验收Gate

## 一、复现发现的真实错误（不是推测）

- 2026-10-30上午A2失败run [40991958267](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40991958267)，B失败run [40991964392](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40991964392)：单测25通过1失败，反例`asof=10-30; freeze_created=11-02T00:55; entry=11-02T09:30`被误放行；`execution_gate`现要求冻结确实在原始asof交易日的17:30后且早于次日09:25。无提前成功归档的信号不得填成交。
- 测试失败后`git add records/national_team_short_ab/`路径尚不存在，造成无意义第二个fatal，已在workflow加路径存在校验，保留pytest真实失败状态。
- 原四ETF CI历史数据测试硬编码最新完整交易日10月27日，真实10月28日全四份额已被10月29日下午归档；修复为对两种已知日期分别校验精确资金值，并对10月29日15:15的股票watch禁止提前读取16:26才首次冻结的V2事件。
- [成功CI run 40994830388](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40994830388)对应最初修复；[最终新增综合合成夹具run 40995281846](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40995281846)实际报告**146项通过**。这两项只说明对应提交的规则和算术静态/历史记录正确，**尚非盘后真实信号冻结**。

## 二、实读开源实现并采纳的做法

| 外部项目与代码证据 | 采用的工程原则 | 本项目对应 |
| --- | --- | --- |
| [VeighNa PaperAccount](https://github.com/vnpy/vnpy_paperaccount) / [开发者文档](https://github.com/vnpy/vnpy/blob/master/docs/community/app/paper_account.md) | 委托、撮合、持仓三种状态分离；模拟单可被拒，仓位独立管理，不得把委托直接当真实成交 | A2/B两个完全独立账本，`PAPER_*_SCENARIO_NO_BROKER_FILL`、`NO_VALID_PAPER_ENTRY`与0真实订单严格分开；缺行情保留拒买/无法验证而不假设成交 |
| [Zipline](https://github.com/quantopian/zipline/blob/master/zipline/finance/slippage.py) | 先有行情事件才允许策略行动；滑点和成交量应在成交层计算，不能后见之明 | 前一日冻结→下一实际交易时点入场；滑点5bps、100股整手、最小券商佣金、卖出印花税单列；B2信号bar须**收完后下一分钟**才能产生模拟入场 |
| [Backtesting.py](https://github.com/kernc/backtesting.py/blob/master/backtesting/backtesting.py) | 止损、止盈作为与持仓关联的OCO/保护单，价格可能在不同顺序触及；不可同K线先择有利方向 | 固定初始ATR止损和2R目标，若一条分钟bar同时含止盈与止损则先止损；不得无故延长T+3 |
| [GitHub Actions concurrency queue](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency) | 默认待执行任务可能被新触发替换，应为关键归档任务配置可排队并独立标识 | A2/B各自`concurrency.queue: max`；每日中国时区18:15、20:15、22:15可重试，所有重试同一日文件不可覆盖 |

以上均为架构/测试对照，**没有复制外部代码或导入不必要的大型交易框架**。

## 三、各层验收门槛，不能串换

| Gate | 验收要求 | 状态 |
| --- | --- | --- |
| G0. 代码正确性 | 最新SHA对应GitHub Actions真实运行，专项对抗测试、旧四ETF账本单测全部通过 | 已有绿灯先例，随新提交需复验 |
| G1. 数据时点 | 某实际交易日17:30之后成功拉取该日全部候选OHLC、历史已归档全四ETF净申赎，生成含`signal_sha256`的不可回写A2/B文件并推送远端 | 待盘后运行，不能提前宣称通过 |
| G2. 市场进入 | 上述Git冻结**实际写入仓库**早于次交易日09:25；下一实际交易日价格/停牌/ST/涨停/整数手/风控全部符合；允许0笔入场，不能事后补单 | 待下一实际交易日 |
| G3. 平仓与对照 | T+1起仅基于事后获得的真实分钟资料进行标明情景性质的止盈止损，T+3 14:50缺资料则不能确认；510300同一入场和退出分钟、费用全扣 | 待成熟 |
| G4. 策略价值 | A2/B各自模拟本金3万元，同期S0配对；报告净超额、回撤、无成交比例和失败日志，长期样本外证明正期望 | 不成熟，绝不宣称可盈利 |

## 四、故意保留的模型限制（下一阶段开发优先级）

1. 目前的B1仍属于日线开盘**模拟价格情景**，不是交易所可撮合订单；尚无独立Level-1/Tick买卖盘、挂单排队数据。B2用收完前一分钟bar后下一分钟开盘情景，防止分钟级未来函数；历史1min源不稳定时可能无成交。
2. 量化滑点的流动性容量上限应在确认`成交量`单位（股/手）后接入，避免错误数量级；可参考Zipline`volume_limit`，不能生搬。
3. `source_flow`是基金全体净申赎代理，不是中央汇金个人成交；原四ETF法人持仓2026期仍缺确证，真实PCF缺失。个股排序只可叫中证指数权重研究代理。
4. A原2026-10-29冻结失败保持原样；A2/B最早新样本是2026-10-30盘后→2026-11-02开盘，不准填报10月30日已过去的09:30成交。

## 五、复核路径

- [MOC](../../MOC.md)、[综合红队](AUD-2026-10-28-e2e-release-gate.md)
- [短线引擎](../../national_team/short_ab_engine.py)、[新增回归](../../tests/test_national_team_short_ab_engine.py)
- [A2 workflow](../../.github/workflows/national-team-short-a2.yml)、[B workflow](../../.github/workflows/national-team-short-b.yml)
- A2不可回写信号计划归档：`records/national_team_short_ab/freezes/A2/`；B计划归档：`records/national_team_short_ab/freezes/B/`。在首次真实盘后冻结成功之前这两个目录**不应存在**，不得为通过Wiki链接检查而制造空白冻结文件。
- [P0 issue #4](https://github.com/lican1213/a-share-momentum-runner/issues/4) 应保持OPEN直至G1/G2实际验证，工程CI通过不代表已完成行情验收。
