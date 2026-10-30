---
id: EXP-0005-A2
type: experiment
status: prospective-paper-implementation-deployed-verification-pending
created: 2026-10-30
updated: 2026-10-30
---
# EXP-0005-A2：严格组原始冻结失效后的前瞻恢复

## 不可回写历史
原EXP-0005指定2026-10-29盘后冻结，未取得有效的远端冻结原件；2026-10-30开盘没有合法的EXP-0005模拟成交。这一事实保留在原实验和GitHub Issue #4中。**A2不是修复了昨天的信号，而是独立的后续样本。**

## 新执行时钟与同日重试
- 仅在**交易日北京时间17:30—23:59:59**、当日收盘行情实际可得时冻结**当日**信号，不允许次日00:55把前日改写为当日已冻结。周末/休市日不冻结。
- Actions在交易日18:15、20:15、22:15尝试执行，第一份成功冻结的`records/national_team_short_ab/freezes/A2/YYYY-MM-DD.json`以独占创建写入，后续重试不得覆盖。失败运行记录独立留存。
- 每次冻结绑定当日完整真实OHLC、10月28日原V2固定S1/S2各五只排序及其哈希、最近已归档完整四ETF同日净申赎代理正值（源最新观察时间必须早于冻结），保留每个源路径、首次可得时刻、提交SHA与GitHub run ID。
- `next_open_session`由上海证券交易所交易日历产生。被冻结的信号在之后**首个实际交易日开盘**才可产生OHLC模拟入场；如果任务未完成源入库，不能计算已买入。
- 模型A2继承A组前日MA20/MA60、10日突破、20日相对收益为正、量比≥1.2。最多S1、S2各一只、单只≤5000元、总仓位≤10000元、100股整手、含费用风险≤150元/笔。
- 入场禁止开盘负缺口和高于前日收盘2%的追价。T+1起止损/2R止盈，T+3 14:50退出必须有完整可靠的1分钟行情；停牌、涨跌停一字板或分钟数据缺失则标记执行不可确认。
- 同一入场日和同一实际退出分钟对照510300 ETF，含各侧3bps佣金最低5元、各侧5bps滑点、股票卖出5bps印花税；只报告OHLC/分钟模拟情景，不认定券商订单成交。

## 实施与验收
- `national_team/short_ab_engine.py --group A2`
- `.github/workflows/national-team-short-a2.yml`
- `tests/test_national_team_short_ab_engine.py`
- 固化运行记录：`records/national_team_short_ab/runs/A2/YYYY-MM-DD/RUN_ID-aATTEMPT.json`
- 若首次冻结失败，保持`NO_VERIFIED_PAPER_FILL`；即使CI单元测试绿灯，也不能升级为收益证据。2026-11-05仅比较真实已经冻结并可核实的后续样本，不把旧实验追溯为成功。
