---
id: SOURCES-REGISTRY
type: sources
status: maintained
updated: 2026-10-28
---
# 来源清单：证据优先于项目README

## 一级证据——本项目运行日志
- [2026-10-28 run 40685553957](../../records/2026-10-28/close/40685553957-a1.json)：45笔假设交易，H01市场条件，退出归因、16项单元测试；记录引用 `source_commit_sha`。
- [2026-10-28 run 40684116228](../../records/2026-10-28/close/40684116228-a1.json)：两指数新浪备选数据通过，全A宽度仍失败。
- [2026-10-28 run 40681563446](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40681563446)：QuantStats索引兼容错误修复后第一次成功的完整脚本运行。
- [运行记录索引](../indices/runs.md)，[完整提交索引](../indices/commits.md)。
- [GitHub Issues：数据和发布门槛](https://github.com/lican1213/a-share-momentum-runner/issues/1)，[H01–H04盈利研究路线](https://github.com/lican1213/a-share-momentum-runner/issues/2)。

## 二级来源——所依赖项目
- [AKShare](https://github.com/akfamily/akshare)：中国股票指数和个股历史行情接口。源码与参数必须匹配实际安装版本。
- [AKQuant](https://github.com/akfamily/akquant)：量化回测引擎。当前只做了API smoke；*三日自定义交易策略没有正式迁移到引擎*。
- [QuantStats](https://github.com/ranaroussi/quantstats)：回撤及收益序列分析；需要检查接口的时间索引类型。
- [BaoStock](https://github.com/baostock/baostock)：独立历史数据备选，不能把“代码支持备选”误写为“每轮实际都用了”。
- [Microsoft Qlib](https://github.com/microsoft/qlib)：点时数据、研究→训练/回测→落地的组织方法，不代表本项目采用Qlib算法。
- [VectorBT](https://github.com/polakowo/vectorbt)：策略信号比较/订单模拟的研究参考。
- [Machine Learning for Trading](https://github.com/stefan-jansen/machine-learning-for-trading)：训练/评估证据边界、概念漂移与前瞻检验研究参考。

## Wiki/MOC 设计来源
- [Better Second Brain](https://github.com/maystudios/better-second-brain)：`raw/wiki/schema`，`index/log/roadmap` 和MOC导航概念。
- [Agent Knowledge — LLM Wiki pattern](https://github.com/limecloud/agentknowledge/blob/main/docs/en/reference/llm-wiki-pattern.md)：只读原始证据、维护Markdown知识、Agent协作协议。
- [LLM Wiki 项目文档](https://llmwiki.cc/docs)：ingest/query/lint 三类基本操作。

**注意**：本文仅借鉴架构，没有在该仓库安装LLM Wiki的npm应用或VectorBT/Qlib完整策略；不能声称存在未执行的代码或运行成效。
