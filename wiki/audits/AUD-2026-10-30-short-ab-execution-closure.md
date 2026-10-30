---
id: AUD-2026-10-30-short-ab-execution-closure
type: audit
status: pending-real-market-verification
created: 2026-10-30
updated: 2026-10-30
---
# A2/B short paper closure: execution and adversarial repair

A original, V2 frozen candidates and existing A2/B strategy parameters are unchanged. No backdated trade.

The ten original ranked securities now carry explicit daily filter results, rejection reasons and per-symbol vendor errors. An unverified candidate never counts as a verified rejection or licenses promotion of a lower-ranked candidate. Unaffected arms still generate independently verified paper candidates.

After prior freeze is demonstrably Git-archived before next 09:25, the first post-close scenario creates append-only entry and exit JSON events in records/national_team_short_ab/ledger/{entries,exits}/{A2,B}/. Entry terms, initial stop/target, benchmark and exit minute are not silently overwritten. Drift blocks synthetic profit.

Tests prove software behavior; G1 actual close freeze, G2 pre-open archived event, G3 completed minute replay and G4 cost-net outperformance remain separate verifications. No brokerage orders are enabled.

## 2026-10-30 additional adversarial repair

- Removed the synthetic +3% *pre-open* affordability rejection: valid low-gap 100-share orders are evaluated at next-session execution price, not eliminated using hypothetical highest permissible gap. Still rejects provably unaffordable lots and enforces the original entry-time max-position/max-risk limits.
- Prior **and** current ETF observations require timezone-aware per-field point-in-time stamps no later than the freeze; a future-stamped prior share/NAV is not allowed in the four-ETF daily difference.
- Both behaviors have counterexample-based automated tests.

## Independent 16:40 Beijing real-source readiness probe

A separate read-only workflow `national-team-short-probe.yml` probes the completed actual market session, all ten frozen V2 securities, the four-ETF archived event, and 510300/601825/600309 minute vendor reachability. The probe cannot call build_freeze, write a freeze path, generate a paper order, or increment paper positions. It saves `records/national_team_short_ab/probes/` with real run ID, SHA, provider errors and source hashes. This is a data-readiness check only, not G1/G2/G3 evidence.

## 2026-10-30 actual vendor failure and fallback repair

Real read-only source probe [41027686611](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41027686611) at 16:37:58 Beijing obtained verified latest 2026-10-29 four-ETF net-creation proxy 8,742,148,830 CNY and 510300 close 4.065 on 2026-10-30, but **all ten stock OHLC sources** and sampled intraday bars failed Eastmoney push2 rate-limiting; generic A-share name lookup reset connection. These are actual failures, not strategy exclusions.

Remedy: query Shanghai Stock Exchange main-board names via `stock_info_sh_name_code` first, Sina unadjusted daily `stock_zh_a_daily` first for stocks, Eastmoney as secondary with per-process rate-limit circuit breaker. For 510300 ETF, prefer existing actual Eastmoney daily with Sina ETF fallback. For 1m exit/B2 evidence, Sina `stock_zh_a_minute` first, then Eastmoney only if not rate limited. Exact 1-minute completeness and terminal-bar validation remains mandatory. Never use historical daily close in place of a 14:50 bar. Fallback itself is not an assertion of available real market quotes; rerun actual probe and validate real evidence.

2026-10-30 16:43 second real probe: ETF vendor intermittently returned a stale prior trading date, despite earlier 16:37 current-date 510300 success. Every daily provider now explicitly requires the requested actual as-of session before being accepted; if stale, try independent alternate provider, else refuse paper evidence.

Extra diagnostics: on 2026-10-30 16:46 the 510300 benchmark was blocked by EM push2 ban and independent Sina ETF path. The prefreeze diagnostic now keeps checking the ten *stock* quotes even if 510300 is missing; such evidence is explicitly STOCK_ONLY_NO_BENCHMARK and produces **no relative strength signal**. A third truly same-security daily provider is tried for sh510300 via Sina securities K-line (not CSI300 index or NAV), with mandatory as-of date validation; unavailable data remains a hard business gate.

## Reconstructing the ETF daily bar only from verified full 1-minute OHLC

10/30 real probe verified 510300, 601825, 600309 minute history each with 230 bars THROUGH 14:50 (source-run 41028928457); ten stocks had genuine 10/30 Sina daily prices, official SSE names were available. However Sina 510300 ETF daily lagged one session. The engine now accepts a 510300 day bar appended to genuine Sina historical daily bars **only** if `stock_zh_a_minute(symbol='sh510300', period='1', adjust='')` supplies at least 238 validated 1m observations, ordered from 09:30 to an exact 15:00 terminal bar for the same actual session. Daily open/high/low/close and volume are constructed strictly from that complete session; the raw minute sequence is separately SHA-256 hashed and the combined derived daily data is provenance-labeled. An incomplete 14:50/14:59 snapshot is rejected, never treated as closing price. CI success is not proof that such 15:00 data were actually available, so rerun the real probe.

## 2026-10-30 real G0 and source provenance, tracked under MOC

Actual GitHub source probe [41029341126](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41029341126) at 16:52:26 Beijing verified 510300 2026-10-30 close 4.065, 10/10 original V2-stock genuine completed daily OHLC, official SSE main-board name roster and 3/3 minute excerpts for 510300,601825,600309. Latest positive full four-ETF factor is 2026-10-29 +8,742,148,830 CNY from immutable merge first archived 2026-10-30 15:14. Indicator-only A2 eligible [601919,601166,600519], B eligible [601825,600309,600000,601919,601166,600519,601838], without individual order-lot/risk or next-day execution validation. 600519 price 1392.05 exceeds 100-share budget. Frozen event now persists ETF provider, reconstructed historical-prior+full15:00-minute source hash, original 510300 as-of closing price; later evaluation checks benchmark as-of close for revisions. G1 actual >=17:30 freeze and G2 Git-archive-before-next-09:25 still pending, never marked as fills.

## 2026-10-30 Sol P0 四项反例修复：真实Actions证据（最新）

**执行引擎最终源码提交**：[`543f6dacaac5af38ccdbfe00234e12d54d50df76`](https://github.com/lican1213/a-share-momentum-runner/commit/543f6dacaac5af38ccdbfe00234e12d54d50df76)。选股条件、原V2十只顺序、手续费与T+3策略未调参。后续main提交为文档与不可回写run记录，不属于不同的源码逻辑版本。

**匹配SHA真实软件验收：**
- [A2 41044988928](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044988928) SUCCESS，`60 passed`，19:01北京时段重跑返回`EXISTING_FREEZE_UNCHANGED`、`errors=[]`、run原件已写回。
- [B 41044988855](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044988855) SUCCESS，`60 passed`，相同代码SHA，原冻结未覆盖。
- [四ETF综合回归41044988939](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044988939) SUCCESS，`182 passed`。
- [MOC Wiki最终运行41045287544](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41045287544) SUCCESS，文档main提交`ec09660fc2b5`。故**G0通过**。

**G1真实执行并核验原件**：10月30日18:54，A2 [run 41044087760](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044087760) / [原冻结](../../records/national_team_short_ab/freezes/A2/2026-10-30.json)（原代码SHA`40640bb97e4b`）完整10/10候选、0 UNVERIFIED，冻结601166及601919；B [run 41044087791](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044087791) / [原冻结](../../records/national_team_short_ab/freezes/B/2026-10-30.json)同源完整10/10，冻结601825、600309、600000。两组资金观察日均为10月29日，首个可能模拟入场11月2日。**不覆盖原冻结或将后续P0修复强行标记成旧G1运行代码**。

**逐项P0验证：**
1. 10/10未知供应商失败不能再建立正式冻结；已核验的S1或S2可以独立不可回写冻结，另一组在同一日继续重试，恢复后只补剩余候选；完整已知却无资格者可创建合法现金冻结。不存在跨数据失败“消耗”ETF资金事件。
2. 分钟源以两种明确分钟标注惯例验证09:30—11:30 / 13:00—15:00精确分钟集合；缺10:00、缺14:55、午休非法时刻、重复/缺开盘或15:00均拒绝交易或收益；510300一分钟合成的收盘价亦遵循同一检验。
3. T+1与T+2一律回看至15:00，包括14:55止损和14:58止盈；只T+3按14:50强制退出；同一分钟的510300基准同步读取。
4. 组内连续资金事件的`cash_available`、`gross_active`、`active_codes`、最多仓位数量从`ledger/entries`和`ledger/exits`真实回读并重建；单次行情服务器失败不释放旧仓，重复股票不能占第二份资金，只有有独立退出证据才在后续交易日释放资金；费用/滑点计入预算。异常或账本漂移直接阻止后续模拟交易。

**G2/G3/G4继续保持OPEN**：11月2日需进一步核验19:00之前归档确实早于11月2日09:25、实际开盘价格、100股整手和可成交性；T+1/T+2整日分钟及T+3 14:50真实分钟退出成熟后再计算与510300配对利润；尚无真实券商订单或纸面成交证明。源差异、真实PCF及最新汇金法人持仓依旧未解决。
