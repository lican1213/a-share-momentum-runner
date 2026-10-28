---
id: OPEN-QUESTIONS
type: open-questions
status: active
updated: 2026-10-28
---
# 尚未搞定的问题与验收门槛

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
