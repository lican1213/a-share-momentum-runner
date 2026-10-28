---
id: ADR-0002
type: decision
status: active
updated: 2026-10-28
---
# ADR-0002：所有输出以实际运行记录为证据，缺失则失败关闭

**决定**：数据检索或代码执行失败时继续出具运行失败报告，但不生成数值买卖指令、历史“成功回测”或虚构实时行情。每个数值说明实际数据源、日期、窗口、模拟交易假设和对应run/commit。

## 数据层优先级
1. `records/` 的逐次带ID证据与其 `source_commit_sha`；GitHub Actions job logs记录实际执行状态。
2. `wiki/` 为可修订的综合解释，不自动修改原始逐次证据。
3. 仅引用网页行情或源码文档不能声称“我运行了代码”。

**原因**：曾发生 GitHub App `403 Resource not accessible by integration`，东方财富行情/市场宽度接口断连，Sina交易日接口偶发失败，QuantStats 0.0.86传入整数索引触发 `TypeError: int - Timedelta`。详见 [INC-0001](../incidents/INC-0001-bootstrapping.md)。

## 关键术语
- **真实数据回放**：对真实历史数据执行程序，用模型假设价位估算历史交易；仍非真实订单。
- **引擎烟雾测试**：当前AKQuant被运行，但只是演示API可用，不代表本模型策略已经用AKQuant执行。
- **实际交易**：带订单ID、成交回报、佣金/税费的券商真实交易。目前无。
- **时间分割**：当前已有2026年最近约6个月保留区间；由于观察股票池、方案已被研究，不是未触碰的OOS。
- **CI通过**：测试和脚本成功，不证明统计显著或未来正收益。

**变更和日志维护**：程序升级须记录新的SHA、回滚路径、错误/疑难引用到 [版本台账](../models/registry.md)、[日志](../log.md)，必要时另开INC/ADR。
