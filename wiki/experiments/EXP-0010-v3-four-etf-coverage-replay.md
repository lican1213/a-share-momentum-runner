---
id: EXP-0010
type: experiment
status: unverified
updated: 2026-11-01
---
# EXP-0010｜V3 原四ETF覆盖率主指标及2021—2026历史事件自动回放

**预注册于 2026-11-01。** 基线代码 SHA：`d28971a027751ba8c9eb13cbcb07010e0f8e911a`。继承 [ADR-0006](../decisions/ADR-0006-coverage-ratio-primary.md)，不变更任何旧A2/B执行层或2026-10-30冻结记录。

## 固定假设与失败条件

- 原始**第一指标**：`Σ(四ETF当日份额×各自当日NAV) / 沪深300当日普通流通市值`；自由流通市值为独立敏感性列。成分代码只允许 `510300/510310/510330/159919`，不能用9ETF或指数价格假替市值分母。
- 逆势承接候选：沪深300过去5日跌，**或**从最近20日收盘高点回撤≥5%；真实覆盖率的1日和5日变化均正，且按逐日NAV计算的ETF申赎代理1日和5日都为正。这个组合仅是**预注册研究假设**，并非最优化参数。
- 基于份额的较弱A组：四ETF总份额较前1/5交易日均正，同时处下跌环境；不能把该代理命名为覆盖率。D组：同样的下跌环境，不考虑资金。三组分别去重（10个完整交易日内不把重复触发日当独立交易）。
- 时点与标签：t日晚的数据**不得在t收盘前用**；以t+1有机会披露、t+2收盘作为保守入场代理，评估之后5/10/20个交易日沪深300收盘方向。原始覆盖率分母的公布时点晚于t+1 15:00，则该t的覆盖率候选不生成。历史份额缓存与历史NAV的首次对外发布时间尚无逐日独立证据，全部研究输出均标 `RETROSPECTIVE_PIT_UNVERIFIED`。
- **失败门槛**：正式F1/F2 10日成本后跑赢同期510300/普通抗跌股的独立事件数≥100、命中率≥60%、相比无资金对照增量≥5百分点；同时披露Wilson 95%区间、5/20日、逐年和连续阴跌失败日。当前执行仅有**指数方向诊断**，达不到上述股票净超额的验证层次即不能宣布模型过关。禁止在见过2022失败后追改阈值。

## 可运行实现

1. [覆盖率与事件纯计算](../../national_team/coverage_v3.py)；[可执行历史回放与溯源hash](../../scripts/replay_national_team_v3.py)；[对抗单测](../../tests/test_national_team_coverage_v3.py)。
2. [V3实际公开数据GitHub Actions](../../.github/workflows/national-team-v3-replay.yml)：在GitHub Runner下载开源份额缓存与CSI300收盘，计算每源SHA256；尝试经AKShare/东财抓取四ETF逐日历史NAV（回溯值，不捏造首次公开时间），运行对抗测试，审计源完整性，最终每次只**追加** `records/national_team_v3/YYYY-MM-DD/RUN-aATTEMPT.json`，不覆盖原件。
3. [普通/自由流通市值输入契约](../../data/national_team/csi300_float_mv.csv)：CSV按 **每日期、每类型一行**，字段为 `date,kind,value_cny,index_code,unit,source_url,published_at,method`。`kind`仅两种 `CSI300_ordinary_float_mv / CSI300_free_float_mv`，`index_code=000300.SH`，`unit=CNY`，所有金额以**元**计、来源须有HTTPS、发布时间须有时区；禁止沿用一个月/一天的值填每天。只有此文件获得真实来源行，历史覆盖率才有具体数值；否则纯份额事件照常复盘，覆盖率事件明确为0、覆盖率天数0。
4. 原始ETF算术既有唯一合同：[core_flow_factors.py](../../national_team/core_flow_factors.py)；此回放为历史P0/P1事件层，另保留5日**逐日NAV加权**之和而非只用期末NAV的5日差。
5. 样本中若缺少159919、每日NAV、分母、公示时刻，逐字段记录；若份额暴变伴随NAV近似逆比例变动，疑似拆并日不产生当日净申购信号。禁止日历前填、分母后验跨日套用、未到期20日视为0收益。

## 首次执行状态

模型、数据合约、GitHub Actions、对抗测试首次提交后，**须以新提交SHA匹配真实完成的Actions run**，再填实际 `share_proxy` / `downturn_control` / `coverage_primary` 去重簇数及命中率。早期 [EXP-0009](EXP-0009-four-etf-share-proxy-60pct-historical-pilot.md)份额初测53簇、5日56.6%、10日49.1%采用当时缓存交集和10日成熟截点；本版改用指数交易日的严格连续性、20日成熟状态和当时上游缓存快照，**结果可能不同，不能直接视为新版运行结果**。

**未解决的实质P0**：权威日度沪深300普通流通/自由流通市值的历史来源和发布日期；四ETF每交易日官方NAV首次公开时刻与拆并确认。只有净份额历史缓存还不足以验证用户最初的覆盖率指标及60%净收益目标。下一工程步骤是向该CSV追加逐日真正核验的数据，随后重算覆盖率与F1/F2点时低位股超额收益。

[根MOC](../../MOC.md) · [历史先导EXP-0009](EXP-0009-four-etf-share-proxy-60pct-historical-pilot.md) · [开放问题](../open-questions.md) · [Wiki日志](../log.md)
