---
id: OPEN-QUESTIONS
type: open-questions
status: active
updated: 2026-10-31
---
# 尚未搞定的问题与验收门槛

**2026-10-31 新增低位跟随研究P0：** [EXP-0007预注册计划](experiments/EXP-0007-flow-absorption-low-entry-plan.md) / [ADR-0005](decisions/ADR-0005-low-entry-research.md)已归档，未实现。下一步必须：①验证原四ETF连续份额/NAV、公司行动和实际首次可得时间；②构建历史CSI300点时成分、价格收益/MA20与PCF来源质量；③独立F1左侧和F2弱确认及S0/无资金对照；④12类红队反例、实际GitHub CI、完整T+1/T+3分钟可执行账本；⑤至少30个非重复事件簇和5/10/20日成熟收益证据。**严禁将旧A2/B高涨突破股或尚未落实的F1/F2称为国家队低位新买点。**

**2026-10-30第二轮优先未解决项（先于以下旧清单）：** [独立审计与修复](audits/AUD-2026-10-30-round2-independent-redteam.md) R1入场未知后账户错误放资、R2跨日重复ETF事件、R3恢复重复同分支、R4 14:50时间标签、R5 V2缺失股票变现金伪超额。必须新5红测转绿、全库旧例无退化、匹配最新SHA的Actions、原始冻结文件逐字不变。真实2026-11-02 G2/G3还未发生。**不可说206项旧CI已覆盖以上缺陷。**

**2026-10-30当前主线：** [唯一当前状态页](current-status.md) · [P0最新执行审计](audits/AUD-2026-10-30-short-ab-execution-closure.md) · [A2严格组](experiments/EXP-0005-A2-prospective-freeze-recovery.md) · [B积极组](experiments/EXP-0006-national-team-aggressive-paper-ab.md)。四项优先软件缺陷已编入引擎与反例：未知数据不得冻结、分钟不得有任何空洞、T+1/T+2必须直到15:00、连续正资金事件必须共享单一组内现金/持仓/费用账本。2026-10-30 A2/B 盘后首个G1冻结原件已确认；新代码G0需匹配SHA CI，11月2日的G2模拟成交及随后G3/G4利润均待观察。**以下旧三日追涨表格仅属历史任务，不再是下个Agent首要待办。**

**优先级变更（2026-10-28）**：先完成[国家队跟踪MVP Issue #3](https://github.com/lican1213/a-share-momentum-runner/issues/3)与[ADR-0003](decisions/ADR-0003-national-team-pivot.md)，建立9只ETF的官方每日份额/基金持有人登记，厘清能否跟随盈利。下表是旧三日追涨研究的历史任务清单，除非安全/证据修复，暂不投入开发资源。


| 优先级 | 问题 / 拦路因素 | 最低证明方式 | 关联 |
| --- | --- | --- | --- |
| P0 | 当前回放仅用12只存续股票，存在样本选择和幸存者偏差 | 重建每个历史日期当时的股票池，包括退市、ST、IPO期限、板块适用规定，点时回测后再审 | [Issue 1](https://github.com/lican1213/a-share-momentum-runner/issues/1) |
| P0 | 缺少14:50分钟可执行价、跌停排队、真实限价成交顺序 | 具有时间戳的分钟数据、明确定价与委托假设，验证真实T+1和T+3卖出可行性 | [EXP-0001](experiments/EXP-0001-baseline.md) |
| P0 | H01过滤后仍然亏损 | 原样冻结规则，寻找新的**未看过**日期和点时股票池，统计真实前瞻净回报和回撤 | [EXP-0002](experiments/EXP-0002-regime.md) |
| P1 | 东财接口全A市场宽度不稳定 | 找到有市场覆盖与交易时点证明的独立来源，数据缺失即不授权交易 | [数据协议](data/contracts.md) |
| P1 | 13笔跳空止损贡献66.81%的亏损绝对收益额 | 独立测量隔夜波动尾部、同入场退出方案、组合仓位约束，不得消除坏单 | [EXP-0001](experiments/EXP-0001-baseline.md) |
| P1 | 两融余额、ETF份额/NAV未验证 | 同交易日同口径的真实返回，注明采集与公布时刻 | [数据协议](data/contracts.md) |
| P1 | 历史信号和真实持仓对账未建立 | 冻结每次候选、触发/未触发、T+1–T+3到期，区分paper与broker fill | [ADR-0001](decisions/ADR-0001-no-trade.md) |
| P2 | GitHub cron可能晚于预定北京时间 | 每轮比较scheduled vs started vs exchange data timestamp；不能默认准点 | [操作指南](operations/handoff.md) |
| P2 | MOC索引与每次模型变更可能漂移 | CI索引自动生成、Wiki内部链接检查、升级前后文档强制审计 | [维护规则](../KNOWLEDGE.md) |

**下一次Agent推荐从P0开始**。必须报告：什么已验证、什么仅被猜测、下一步实测证据在哪。未达标不改仓库交易信号开关。

研究议程：[盈利研究Issue 2](https://github.com/lican1213/a-share-momentum-runner/issues/2)。
