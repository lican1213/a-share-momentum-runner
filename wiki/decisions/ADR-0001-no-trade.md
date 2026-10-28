---
id: ADR-0001
type: decision
status: active
updated: 2026-10-28
---
# ADR-0001：任何未通过独立验证的模型只允许研究信号

**决定**（2026-10-28）：`signals.json` 正式交易列表必须空；`research_candidates` 可报告为研究观察，不可包装为买入价建议；不得自动调用券商下单。仓库代码中的模型授权门槛优先于任何提示词的“每天必须推荐”。

**理由**：45笔历史代理交易净收益平均−0.2769%，12只现存固定股票引入幸存者偏差；T+3以日收盘替代14:50，未建立严格样本外优势；全A宽度和两融等部分关键源失效。对应 [EXP-0001](../experiments/EXP-0001-baseline.md) 与 [EXP-0002](../experiments/EXP-0002-regime.md)。

**实施**：[commit 6a37758538a8](https://github.com/lican1213/a-share-momentum-runner/commit/6a37758538a8) 设置研究态；[实际运行](../../records/2026-10-28/close/40685553957-a1.json) `signals.status=RESEARCH_ONLY_NOT_TRADE_AUTHORIZED` 和 `signals=[]`。

**废止条件**：必须新ADR+新的代码变更评审；确认真实时点全股票池、盘中真实执行代理、税费和涨跌停、独立前瞻/走步验证、成本后比较优势和稳定回撤，且获得明确授权。仅盈利几笔或回测指标好看不够。

**与另一策略分离**：红利/保险费用覆盖类长期思路不是T+3突破信号，不混用数据、交易日与风险预算。
