---
id: COMPILED-BRIEFING
type: overview
status: maintained
updated: 2026-10-28
---
# 国家队资金→成分股研究 Agent 最新证据简报

[根MOC](../../MOC.md) · [国家队所有实跑记录](../indices/national-team.md) · [模型演进](../models/registry.md) · [红队审计](../audits/AUD-2026-10-28-e2e-release-gate.md)

**主线：中央汇金等法定主体披露（低频） × 固定四沪深300ETF资金份额（高频） → 指数/PCF对应股票 → S0 ETF基准 vs S1/S2选股组合。**

- 最新ETF源采集尝试：[run 40710985962](../../records/national_team_etf/2026-10-28/40710985962-a1.json)；状态 `PRIOR_FULL_FOUR_AND_LATEST_PARTIAL_OBSERVED`；日期 2026-10-28。
- 最近可完整核验四ETF份额/NAV的历史记录：[run 40710985962](../../records/national_team_merged/2026-10-28/40710985962-a1.json)；状态 `PARTIAL_LATEST_WITH_PRIOR_FULL_FOUR_FACTOR`；日期 2026-10-28。
- 最近完整基金资金研究日：**2026-10-27**；合计当日净份额×NAV代理 **5612203530.000000 元**；这不是汇金个人账户当日买入。
- 最近完整5日资金强度：**0.2910660540851112994085114550**；基金NAV尚需发行人原件复核、份额拆并需独立验证；极值应标异常而非直接买点。
- 最近真实指数权重代理股票观察名单：[run 40710985962](../../records/national_team_watch/2026-10-28/40710985962-a1.json)；状态 `INDEX_PROXY_RESEARCH_WATCHLIST`；日期 2026-10-28。
- 最新实测股票样本数：**150**；指数权重覆盖约 **0.83015**；指数权重非ETF真实PCF，且未证明个股跟随收益。
- 最近四ETF独立V2前瞻选股：[run 40719359363-a1-v2](../../records/national_team_strategy/2026-10-28/40719359363-a1-v2.json)；状态 `FROZEN_PROSPECTIVE_RESEARCH`；日期 2026-10-28。
- V2真实首次可得时刻：2026-10-28T23:46:43.818303+08:00，底层四ETF资金日：2026-10-27；S1资金/成交额研究组 **601825, 600000, 601229, 601166, 600519**；S2独立价格确认研究组 **600309, 601919, 600660, 601012, 601838**。
- V2仅以资金为择时触发（CSI300代理权重跨ETF相同，不能辨识逐股票实际买盘）；5/10/20日净超额收益待未来真实行情成熟；旧V1组合不可替换初始冻结股单。
- 最近PCF采集尝试：[run 40710985962](../../records/national_team_pcf/2026-10-28/40710985962-a1.json)；状态 `SSE_PCF_FETCHED_BUT_NOT_VERIFIED`；日期 2026-10-28。
- 最近纸面事件冻结：[run 40719516083-a1-v2](../../records/national_team_events/2026-10-28/40719516083-a1-v2.json)；状态 `NO_NEW_V2_EVENTS`；日期 2026-10-28。
- 最近纸面收益观察：[run 40710985962-a1](../../records/national_team_paper/2026-10-28/40710985962-a1.json)；状态 `PAPER_EVALUATION_ATTEMPTED`；日期 2026-10-28。
- 最近独立实跑红队审计：[run 40710985962-a1](../../records/national_team_audits/2026-10-28/40710985962-a1.json)；状态 `RESEARCH_PRIOR_FOUR_CURRENT_PARTIAL_AUDITED`；日期 2026-10-28。

**投资结果状态：暂无独立样本外净超额收益验证；不推断任何国家队真实账户买卖、已成交订单或必然盈利。**

自动页面仅汇总已保存的证据。最新综合workflow是否为绿色，仍需单独查GitHub Actions对应SHA。
