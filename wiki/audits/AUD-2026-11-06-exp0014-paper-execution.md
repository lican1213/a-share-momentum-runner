---
id: AUD-2026-11-06-EXP0014-EXECUTION
type: audit
status: verified_with_market_data_pending
updated: 2026-11-06
---

# 2026-11-06：EXP-0014 V5模拟盘执行与S0配对对抗审计

**范围：** [纸面账户引擎](../../national_team/paper_account_v5.py)、[逐笔对抗测试](../../tests/test_national_team_paper_account_v5.py)、[EXP-0014协议](../experiments/EXP-0014-v5-paper-account.md)。固定四ETF资金主指标、V5首次可得冻结、左侧/右侧选股和全部不可覆盖`records/`未改。

## 实际证据和失效复现

1. **S0配对时点：** 旧逻辑股票开盘跳空止盈/止损，却拿510300当日收盘价当同步退出。修为同日ETF开盘代理；盘中触发无法逐分钟配对，保留ETF日高低收益界限及明确的非同步标签；T+2收盘用同日收盘代理。
2. **整手本金不同：** 股票和ETF整手投入额可能不等，原人民币盈亏直接相减不代表等额净超额。新增扣费后的ETF净收益率按股票实际买入成本归一字段`excess_s0_equal_capital_cny`，保留旧整手`excess_s0_cny`便于对账。归一化是研究收益比较，不把非整手数当实际ETF订单。
3. **真实源竞态：** [首次合并后主链#42179483457](https://github.com/lican1213/a-share-momentum-runner/actions/runs/42179483457)于北京11/06 15:14产出的[原始快照](../../records/national_team_paper_accounts_v5/2026-11-06/42179483457-a1.json)已经推进510300交易日到11/06，股票价格仍只标11/05，三组`STALE_PRICE`、0已平仓。旧代码后续排除`last_market_session`以前的日子，即使股票11/06日线后来补齐，也永远漏掉预定T+2平仓；更可能拿11/09价假作T+2。
4. **红队先失败后修复：** 新测试在旧代码分别复现“迟到股票日线永远不平仓”和“跳过缺价日、把后一天标T+2”两个失败。新代码按仓位逐日保留`pending_ohlc_sessions`，补齐时只重新核算事前固定的**退出**情景，平仓写`late_ohlc_reconciliation=true`；缺早一日价格不拿后一日价格冒充。缺入场价仍永不补买；重复运行不重复订单或现金。

## 真实Gate与新生产运行

| 证据 | SHA / Run | 结果 |
| --- | --- | --- |
| S0首轮完整PR对抗门 | [`fda261d`](https://github.com/lican1213/a-share-momentum-runner/commit/fda261d65add97029e82c11bd4705534077353ad) · [#42179226710](https://github.com/lican1213/a-share-momentum-runner/actions/runs/42179226710) | 287 passed、Wiki 48页有效 |
| S0首轮合并后真实主链 | [`fea1a7f`](https://github.com/lican1213/a-share-momentum-runner/commit/fea1a7f9357b7a3271b76dfd5ea9b3ee8a8ff753) · [#42179483457](https://github.com/lican1213/a-share-momentum-runner/actions/runs/42179483457) | 33个专项测试通过，原始账户JSON落盘；暴露源竞态 |
| 迟到日线PR对抗门 | [`1acff55`](https://github.com/lican1213/a-share-momentum-runner/commit/1acff558fdf0fcf2bd32352ae747d734645d43c6) · [#42180295638](https://github.com/lican1213/a-share-momentum-runner/actions/runs/42180295638) | 289 passed、Wiki 48页有效 |
| 最终合并main全库门 | [`ce1fe4f`](https://github.com/lican1213/a-share-momentum-runner/commit/ce1fe4fa8bf206a730c35cc63f7dd3194c1e0c6d) · [#42180430286](https://github.com/lican1213/a-share-momentum-runner/actions/runs/42180430286) | 289 passed、Wiki 48页有效 |
| 最终main真实模拟运行 | 同SHA · [#42180430149](https://github.com/lican1213/a-share-momentum-runner/actions/runs/42180430149) | 35项专项测试，新的[不可覆盖账本](../../records/national_team_paper_accounts_v5/2026-11-06/42180430149-a1.json)落盘 |

**最新实盘模拟状态（北京时间11/06 15:23）：** 510300日历已到11/06，股票同日完整OHLC仍未齐，浅跌、深跌、右侧三组各2只持仓、0已平仓，分别有2个待补价格日；权益按11/05最近已得收盘约30,015.72、29,961.61、30,006.85元，`mark_status=STALE_PRICE`。绝不能把它们报为11/06收盘后真实盈亏、已实现超额或券商成交。等后续同源股票OHLC归档，才可观察迟到日线退出分支的**真实业务验收**；289测试通过证明的是程序约束，不是已经产生盈利。

**剩余可观察缺口：** 分钟价不足以证明盘中止盈/止损和S0同刻成交；11/06股票报价迟到，`late_ohlc_reconciliation=true`分支尚待有源恢复的真实账本检验。没有删除或改写旧快照，也没有授权任何真实券商下单。
