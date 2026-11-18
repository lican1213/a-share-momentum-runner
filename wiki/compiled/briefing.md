---
id: COMPILED-BRIEFING
type: overview
status: maintained
updated: 2026-11-19
---
# 国家队资金→成分股研究 Agent 最新证据简报

[根MOC](../../MOC.md) · [国家队所有实跑记录](../indices/national-team.md) · [模型演进](../models/registry.md) · [红队审计](../audits/AUD-2026-10-28-e2e-release-gate.md)

**主线：中央汇金等法定主体披露（低频） × 固定四沪深300ETF资金份额（高频） → 指数/PCF对应股票 → S0 ETF基准 vs S1/S2选股组合。**

- 最新ETF源采集尝试：[run 44357830201](../../records/national_team_etf/2026-11-19/44357830201-a1.json)；状态 `PRIOR_FULL_FOUR_AND_LATEST_PARTIAL_OBSERVED`；日期 2026-11-19。
- 最近可完整核验四ETF份额/NAV的历史记录：[run 44357830201](../../records/national_team_merged/2026-11-19/44357830201-a1.json)；状态 `PARTIAL_LATEST_WITH_PRIOR_FULL_FOUR_FACTOR`；日期 2026-11-19。
- 最近完整基金资金研究日：**2026-11-17**；合计当日净份额×NAV代理 **11600864910.000000 元**；这不是汇金个人账户当日买入。
- 最近完整5日资金强度：**0.03560723142042751806095846946**；基金NAV尚需发行人原件复核、份额拆并需独立验证；极值应标异常而非直接买点。
- 最近真实指数权重代理股票观察名单：[run 44357830201](../../records/national_team_watch/2026-11-19/44357830201-a1.json)；状态 `INDEX_PROXY_RESEARCH_WATCHLIST`；日期 2026-11-18。
- 最新实测股票样本数：**150**；指数权重覆盖约 **0.82681**；指数权重非ETF真实PCF，且未证明个股跟随收益。

**当前研究执行主线：V3资金 → V5路由 → 连续模拟盘；旧V2/A2/B仅历史归档。**
- V3最新回放：[run 44366889352-a1](../../records/national_team_v3/2026-11-18/44366889352-a1.json)；状态 `UNVERIFIED`；日期 2026-11-18。
- V5最新事件路由：[run 44367015374-a1](../../records/national_team_router/2026-11-19/44367015374-a1.json)；状态 `ALREADY_FROZEN_FOR_SESSION`；日期 2026-11-19。
- V5最近不可回写冻结：[run 44358857196-a1](../../records/national_team_left_entry_v5/2026-11-19/44358857196-a1.json)；状态 `UNVERIFIED`；日期 2026-11-19。
- V5最新独立前瞻路径：[run 44367415961-a1](../../records/national_team_left_outcomes_v5/2026-11-19/44367415961-a1.json)；状态 `UNVERIFIED`；日期 2026-11-19。
- V5最新模拟账本：[run 44367415961-a1](../../records/national_team_paper_accounts_v5/2026-11-19/44367415961-a1.json)；状态 `UNVERIFIED`；日期 2026-11-19。
- 指数交易日 2026-11-18；最新完整四份额日 2026-11-18；普通覆盖率有效日 16，历史PIT核验日 0；最新分母采集 SOURCE_UNAVAILABLE；当前ratio=None。
- 资金观察交易日 2026-11-18；路由 ALREADY_FROZEN_FOR_SESSION；资金模式 SHARE_PROXY；同额成熟10日独立簇 1/8；默认组 SHALLOW_DIP。
- 账户市场日期 **2026-11-18**；捕获 2026-11-19T02:14:55.620406+08:00；纸面非券商成交。

| 组 | 现金 | 权益 | 持仓数 | 平仓数 | 扣费净盈亏 | 同额S0已实现超额 | mark_status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SHALLOW_DIP | 25971.30 | 30039.22 | 1 | 3 | 39.22 | -39.06 | CURRENT_CLOSE_PROXY |
| DEEP_DIP | 24227.14 | 29882.47 | 2 | 3 | -117.53 | -43.23 | CURRENT_CLOSE_PROXY |
| R_BOUNCE | 21743.02 | 30004.74 | 2 | 3 | 4.74 | 6.26 | CURRENT_CLOSE_PROXY |
| EARLY_ENTRY | 22674.35 | 29998.01 | 2 | 0 | -1.99 | None | CURRENT_CLOSE_PROXY |

**历史归档（不作为当前新信号）：**
- 最近四ETF独立V2前瞻选股：[run 41027617348-a1-v2](../../records/national_team_strategy/2026-10-30/41027617348-a1-v2.json)；状态 `FROZEN_PROSPECTIVE_RESEARCH`；日期 2026-10-30。
- V2真实首次可得时刻：2026-10-30T16:36:55.609229+08:00，底层四ETF资金日：2026-10-29；S1资金/成交额研究组 **601825, 600000, 601229, 600519, 601166**；S2独立价格确认研究组 **002714, 600660, 002422, 688111, 601318**。
- V2仅以资金为择时触发（CSI300代理权重跨ETF相同，不能辨识逐股票实际买盘）；5/10/20日净超额收益待未来真实行情成熟；旧V1组合不可替换初始冻结股单。
- 最近PCF采集尝试：[run 44357830201](../../records/national_team_pcf/2026-11-19/44357830201-a1.json)；状态 `SSE_PCF_FETCHED_BUT_NOT_VERIFIED`；日期 2026-11-19。
- 最近纸面事件冻结：[run 41369083901-a1](../../records/national_team_events/2026-11-02/41369083901-a1.json)；状态 `ALL_EVENTS_DUPLICATE_PREVIOUSLY_FROZEN`；日期 2026-11-02。
- 最近纸面收益观察：[run 41369083901-a1](../../records/national_team_paper/2026-11-02/41369083901-a1.json)；状态 `PAPER_EVALUATION_ATTEMPTED`；日期 2026-11-02。
- 最近独立实跑红队审计：[run 41369083901-a1](../../records/national_team_audits/2026-11-02/41369083901-a1.json)；状态 `RESEARCH_DATA_AUDIT_PASS`；日期 2026-11-02。

**投资结果状态：暂无独立样本外净超额收益验证；不推断任何国家队真实账户买卖、已成交订单或必然盈利。**

自动页面仅汇总已保存的证据。最新综合workflow是否为绿色，仍需单独查GitHub Actions对应SHA。
