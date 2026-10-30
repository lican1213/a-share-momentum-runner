---
id: AUD-2026-10-30-ROUND2-INDEPENDENT
type: audit
status: software-repair-in-progress
created: 2026-10-30
updated: 2026-10-30
---
# 第二轮独立审计：R1—R5 执行状态、经济事件、分钟时钟、V2超额收益

**唯一可信基线**：2026-10-30 20:30用户提供的离线审计包在原HEAD `88dfa97dac204bab48b06fb6d6793cdc11e18dea`实际得到5 failed；上轮[全库Run 41045697242](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41045697242)的206 passed真实存在，但其覆盖范围无法否定新增反例。此页记录修复过程，不取代原始失败证据。

## 不变项

- **不得覆盖** [A2 2026-10-30原冻结](../../records/national_team_short_ab/freezes/A2/2026-10-30.json) 或 [B原冻结](../../records/national_team_short_ab/freezes/B/2026-10-30.json)。该G1冻结的来源SHA仍是`40640bb97e4b`，两组都10/10 VERIFIED。首次可能模拟入场日2026-11-02。两份原件并非经纪商成交。
- 原V2十只股票排序、原A2/B策略规则、MA/ATR、整手、费用及冻结资金事件的数值不因修代码而优化。不得事后改变获利概率、回填入场或把四ETF净份额等同于汇金本人买入。

## 五项已复现问题与新代码语义

**R1 历史入场未知变现金**：`NO_FILL_RULE_REJECTED`、`ENTRY_DATA_UNKNOWN`、`CONFIRMED_PAPER_ENTRY`在新引擎中独立。决策首次判断永久写入`ledger/decisions/{A2,B}/<signal_id>.json`，附实际评估时间、原信号哈希和原因。任何前序`ENTRY_DATA_UNKNOWN`立即禁止后续资金事件分配，并禁止随着数据恢复补一个历史模拟单。只允许明确、经审计的`expire_unknown_entry`追加`ledger/resolutions/`退出未知状态，保留原决策不覆盖；在退役生效前本应入场的后续事件不可回填。

**R2 资金事件跨日重复**：所有完整/部分/剩余分支统一根据组、策略版本、四ETF资金日期和分支作用域查询不可回写历史；同一资金日一旦在其他收盘日出现，即拒绝重新冻结，不因文件名不同而创建额外交易机会。

**R3 恢复时重复S1/S2**：同日恢复锁定**整个分支判断**，包括已核验无信号的现金分支，不是仅排除已冻结ticker。恢复冻结只含未锁定的分支；B第三席在部分数据恢复时不另行按最新行情补造。完整原始无缺失事件仍遵循预先选股协议。

**R4 14:50价格时间顺序**：一分钟证据标记`minute_convention=BAR_START/BAR_END`。BAR_START在14:50开盘先执行固定退出，禁止看之后high/low；BAR_END的14:50 OHLC区间在时点之前，若没有先触发止损止盈，则按当刻`close`退出。S0 ETF选择同一真实时刻的open或close；非固定退出时无法配对不同分钟标签的行情即标未知。T+1/T+2仍需完整到15:00。

**R5 V2缺数据伪超额**：若任何冻结股票的入场日OHLC/已核验是否被阻断状态未知，任一期结果为`STOCK_ENTRY_DATA_UNKNOWN`、记录覆盖率、无`paired_excess_net_return`数值；仅显式证据证实未成交的分配可当现金，不可用ETF下跌制造正收益。已有股票出场无数据仍为未验证，不计完整组合利润。

## 分级验收，G0 ≠ G1 ≠ G2 ≠ G3 ≠ G4

- **R0前置红测试**：原代码5个新的纯合成反例全部失败，是真实可复现的代码路径。
- **R1软件回归**：新[独立审计测试](../../tests/test_audit2_independent_redteam.py)覆盖5类失败，以及跨日完整恢复、开始/结束时间标签、部分V2缺数、显式退出未知状态。原206项需全量不退化，且新Actions SHA对应最新源码。
- **G1真实冻结**：现有2026-10-30 A2/B原件与SHA保留；Git写入时间早于2026-11-02 09:25。
- **G2真实入场**：仍需11月2日盘后依据真实市场时间戳、事前已归档冻结、并计佣金/风险/账户状态单独审计。不能从未来完整行情反推当时一定成交。
- **G3/G4**：T+1/T+2全部有效分钟、T+3 14:50确证、配对510300以及长期前瞻净超额仍未成熟。
- **其他研究缺口**：真实PCF、2026国家队法人当期持仓、V2 5/10/20成熟完整覆盖均未解决。

参考：[当前执行状态](../current-status.md) · [实验B协议](../experiments/EXP-0006-national-team-aggressive-paper-ab.md) · [Issue #4](https://github.com/lican1213/a-share-momentum-runner/issues/4) · [修复PR #5](https://github.com/lican1213/a-share-momentum-runner/pull/5)。

**谨记**：每个新真实运行的run ID、head SHA、业务状态、数据SHA和冻结/账本内容应独立核验；不得以软件CI绿色自称有实盘获利。
