---
id: EXP-0012
type: experiment
status: running-automation
updated: 2026-11-02
---

# EXP-0012：四ETF资金事件驱动的低位研究自迭代

**目标：** 跟踪原始四只沪深300ETF（510300、510310、510330、159919）在指数下跌时的持续逆势申购，优先研究近五日仍未上涨的成分股；让真实的未来收益反馈直接决定下一次纸面排序，而不是追涨或增加技术硬门槛。

## 运行链（每天北京时间盘后）

1. 16:20 收集实际ETF/沪深300股票观察源（`national-team-live.yml`）；17:25 V3拉取份额、净值与沪深300行情并重新计算历史事件（`national-team-v3-replay.yml`）。
2. 18:05 路由器（`event_router_v5.py`）寻找最新完整四ETF、沪深300下跌、当日及5日申购代理都为正的日期；只接受真实同日股票观察，按**资金交易日**去重。可接受最多3个自然日的源披露滞后，但冻结发生在实际观察当时，绝不追认历史买入；已在EXP-0011冻结的10/30事件不重开。每天留存路由决定。
3. 只在**新增有效交易日**收集真实最多150股、当日OHLC并冻结EXP-0012纸面名单；不重复旧EXP-0011的银行/钢铁名单。资金主指标继续是四ETF AUM/沪深300**真实普通流通市值**；无分母时保留NULL、明确使用份额×NAV辅助事件。
4. 18:45跟踪最近24个真实冻结日：以后验实际日线开盘价形成**情景**，按统一费率计算F1/F2和同刻510300（S0）3/5/10/20日净超额；未到期仍为NULL。完整来源和每次计算追加不覆盖。

## 预先定义的两个并列纸面策略

- **SHALLOW_DIP（默认）**：合格池中近五日仍跌/未涨优先，先选跌得浅、保持抗跌的股票；其次才考虑小幅上涨的股票。
- **DEEP_DIP（影子）**：完全同一时间、同一股票数据、同一预算/交易约束下，仍跌/未涨优先，先选跌得较深的股票。
- 两者各最多两股，单股参考预算≤5000元、总≤10000元；**F1/F2、S0分开评价**。不会为了排名扩大无数据或不可定价股票的假想仓位。

## 自动反馈与升级

- 每天只使用已成熟、两策略都能与S0成对比较的**第10交易日真实收益**。同一冻结的多次跟踪取最新一份；连续多日若属于同一个资金**事件簇**，只用该簇首次冻结计一次独立样本。
- 少于8个独立成熟事件簇，继续默认SHALLOW_DIP；达到8簇后，若DEEP_DIP平均10日扣费净超额比SHALLOW_DIP至少高0.2个百分点，则**后续新事件自动选择DEEP_DIP**；否则继续SHALLOW_DIP。影子组始终记录，允许新证据自然反向改变选择。规则事前固定，软件不会偷改过去的冻结。
- 方向历史命中率≥50%才允许原V4的小额纸面准入；这不是个股盈利概率；不发真实券商指令。

**源码：** [事件路由](../../national_team/event_router_v5.py) · [双组低位选股](../../national_team/left_entry_v5.py) · [纸面追踪](../../scripts/track_national_team_left_entry_v5.py) · [每日调度](../../.github/workflows/national-team-event-router-v5.yml) · [每日反馈](../../.github/workflows/national-team-left-outcomes-v5.yml) · [专项测试](../../tests/test_national_team_event_router_v5.py)。

**证据：** `records/national_team_router/`、`records/national_team_left_entry_v5/`、`records/national_team_left_outcomes_v5/`。状态由真实Actions的源码SHA/运行ID和不可覆盖记录证明。旧EXP-0011、A2/B完全不修改；原市值分母缺失、基金投资者身份不明继续在数据层标注。

## 2026-11-02：兼容扩展

[EXP-0013](EXP-0013-path-learning-and-retirement.md)在同一V5存储/调度链追加R_BOUNCE独立参考、MFE/MAE与日线备用；不改EXP-0012的左侧双组及8独立成熟簇自动策略选择，旧冻结不变。新记录标记extension_experiment_id与源码SHA。
