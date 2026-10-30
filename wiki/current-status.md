---
id: CURRENT-STATUS-2026-10-30
type: project-status
status: active
created: 2026-10-30
updated: 2026-10-30
---
# 国家队 ETF → 个股机会：单一当前状态与执行 P0 验收门槛

**2026-10-30 20:30新审计优先声明：上轮G0全库206项绿色已被五个新的执行/收益反例证伪其“完整性”，并不代表当时CI伪造。** 当前修复在[第二轮独立审计](audits/AUD-2026-10-30-round2-independent-redteam.md)及[PR #5](https://github.com/lican1213/a-share-momentum-runner/pull/5)。新增状态`ENTRY_DATA_UNKNOWN`必须持久化并暂停后续组内资金，完整/部分冻结同一funding_day去重，已冻结分支不选第二只，14:50按分钟标签时点交易，V2未知行情禁止完整超额收益。将第二轮最新SHA全库测试列为**新G0**，不要把下面历史206项当作最终审计。

**本页是人工维护的状态基线；新Agent先读[MOC](../MOC.md)，再读本页、最新Actions及不可回写JSON。任何新运行可能使下列状态过时，须重新核实当时的run ID/SHA。**

## 目前主线

A. 法定国家队法人持仓披露：2026年最新账户归属未确认，2025年159919持仓不可直接延用。  
B. 原始四ETF 510300/510310/510330/159919：2026-10-29完整已归档，四基金整份额×对应NAV净申购代理+8,742,148,830元，非中央汇金本人资金流。  
C. 股票研究：原2026-10-28首次冻结V2候选仍为S1五只601825、600000、601229、601166、600519和S2五只600309、601919、600660、601012、601838；ETF逐股真实PCF仍未确认，只有指数权重代理。  
D. 真实盈利：5/10/20日V2尚未验证；A2/B短线仍无经核验的纸面成交、无券商订单，净利润和超额收益未成熟。

## 2026-10-30盘后已经有真实G1冻结（不得更改）

| 账户 | 真正GitHub执行 | 源码SHA / 冻结时间 | 已冻结模拟候选 | 冻结JSON |
|---|---|---|---|---|
| A2严格 | [41044087760](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044087760) SUCCESS，57项测试通过 | `40640bb97e4b962ed85fd5abe320fa7c75324524` / 北京时间18:54:05 | 601166、601919 | [原件](../records/national_team_short_ab/freezes/A2/2026-10-30.json) |
| B积极 | [41044087791](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044087791) SUCCESS，57项测试通过 | `40640bb97e4b962ed85fd5abe320fa7c75324524` / 北京时间18:54:04 | 601825、600309、600000 | [原件](../records/national_team_short_ab/freezes/B/2026-10-30.json) |

两份当日完整候选源为10/10 VERIFIED、0 UNVERIFIED，资金日2026-10-29，模拟下一可执行日2026-11-02；原件有`signal_sha256`及首次可得源哈希。**这不是模拟买入**。新引擎修补之后不得重算/篡改这两个既有冻结记录；未来每一笔纸面情景都必须记录原冻信号SHA、该次执行引擎SHA和交易时点。

## 2026-10-30执行层四项P0红队修复

审计基线是[用户提供的2026-10-30任务书](../MOC.md)和此前源码`892db35965da3291d26cb2b9d62984a3ca5a8bf1`。后续修复均保持原十只候选及MA/ATR/仓位阈值不变。

1. **未知数据与正式冻结分开**：10/10未知仅生成可重试诊断，不写正式freeze、不消耗资金事件；10/10明确不达标才允许`VALIDATED_CASH_NO_SIGNAL`。独立S1或S2完整验证时，可仅冻结该臂`YYYY-MM-DD-S1/S2.json`，另一臂继续重试，原臂哈希不可覆盖，完整后仅补剩余候选，不双重计入。
2. **分钟严格完整性**：按日内09:30—11:30、13:00—15:00交易会话核验全部一分钟时间戳，兼容明确的开始分钟/结束分钟两种标签惯例；任何缺中间止损分钟、午休伪造、重复、缺终端均拒绝收益确认。510300由分钟合成的日线也必须具备完整15:00会话。
3. **T+1/T+2尾盘**：两个交易日正常检查到15:00（包括14:55/14:58等分钟）；T+3仍按原协议只到14:50强制退出，并按同分钟510300扣成本配对。
4. **跨日共享账户**：A2/B各自拥有独立3万元账户；`ledger/entries`与`ledger/exits`为现金、费用、开放持仓的唯一真相。每个新事件继承前期冻结的持仓与现金，禁止同股重复、超过A2 1万元/2只或B 2万元/3只的整体上限。真实卖出证据缺失则持续占用额度。已落盘旧仓不能因随后行情供应商失败而消失。账本漂移、中间事件未知、时间戳不确定时关闸而非默认恢复资金。

新回归位于[tests/test_national_team_short_ab_engine.py](../tests/test_national_team_short_ab_engine.py)；实施于[short_ab_engine.py](../national_team/short_ab_engine.py)。完整失败日志和定位记录在[执行闭环审计](audits/AUD-2026-10-30-short-ab-execution-closure.md)；真实完成SHA与Actions请读取最新GitHub运行，而非仅信此页。

**全仓库独立验收（2026-10-30）**：新增[专用全量Gate](../.github/workflows/national-team-p0-full-gate.yml)于真实[GitHub Run 41045697242](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41045697242)（SHA`9b0a78ebf807`，对比执行引擎变动仅新增CI工作流）实际执行`python -m pytest -q`，**206 passed**；`scripts/wiki_lint.py`报告`WIKI_LINT_OK pages=34 ids_unique=true all_internal_links_present=true`，Python语法检查成功。此前的182项子集并未替代这次全量测试。全量G0通过也不能替代G2/G3市场模拟。

## 仍需独立验证的Gate

- **G0（新版本）PASS**：执行引擎SHA `543f6dacaac5af38ccdbfe00234e12d54d50df76`，A2真实Actions [41044988928](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044988928) 60项通过，B [41044988855](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044988855) 60项通过，四ETF综合 [41044988939](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41044988939) 182项通过；后续文档Wiki完整性 [41045287544](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41045287544) SUCCESS。不得与G1实际行情或G2模拟成交混用。
- **G1（10月30日既有历史源）**：A2/B首次完整盘后冻结已通过，原件不可覆盖；之后若来源间歇性断流则应写错误或部分臂合法冻结。
- **G2（11月2日）**：必须核实冻结Git实际写入时间早于09:25，随后按真实开盘OHLC及分钟触发、风险、100股整手、停复牌限制验证模拟成交；实际券商订单仍为0。
- **G3**：T+1/T+2真实完整分钟及T+3 14:50退出，ETF同期同分钟净利润对照；缺分钟不得填确认盈利。
- **G4**：多次独立前瞻事件与S0配对扣成本净超额及回撤；不因一周结果批准实盘。

## 源文件与维护入口

[AGENTS入口](../AGENTS.md) · [开放问题](open-questions.md) · [EXP-0005-A2](experiments/EXP-0005-A2-prospective-freeze-recovery.md) · [EXP-0006-B](experiments/EXP-0006-national-team-aggressive-paper-ab.md) · [模型台账](models/registry.md) · [运行账本索引](indices/runs.md)

任何修改必须在程序、测试、原始记录和文档间形成可审计对应。**CI PASS ≠ 模拟成交 ≠ 国家队本人买入 ≠ 投资收益可复制。**
