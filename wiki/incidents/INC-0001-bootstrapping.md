---
id: INC-0001
type: incident
status: observed
updated: 2026-10-28
---
# INC-0001：首次GitHub部署、权限、行情链路与QuantStats兼容故障

| 发生/观察时间 | 现象 | 根因/判断 | 采取措施 | 结果证据 |
| --- | --- | --- | --- | --- |
| 2026-10-28 | 在空仓库创建README遭 `403 Resource not accessible by integration` | 用户仓库权限不等于GitHub App实际写授权 | GitHub App安装并授予仓库权限，再执行 `create_file` | [成功commit 791919e0](https://github.com/lican1213/a-share-momentum-runner/commit/791919e08565) |
| 2026-10-28 | 初次Actions能装AKShare、AKQuant、QuantStats，行情接口断开 | 数据提供方网络不可用/不稳定 | 增加Sina备选日K、本地交易日、BaoStock研究备选，保留数据源标签 | [INC调查前失败运行](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40680453840) |
| 2026-10-28 | `TypeError: unsupported operand type(s) for -: 'int' and 'Timedelta'` | **确认**QuantStats 0.0.86回撤函数要求日期索引；不是交易日历。最初对故障原因的猜测被证伪 | 在回撤序列使用专门、明确非真实日期的 `DatetimeIndex`，增加回归测试 | [修复commit 7234c871](https://github.com/lican1213/a-share-momentum-runner/commit/7234c871b03c)，[后续成功运行40681563446](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40681563446) |
| 2026-10-28 | 东方财富指数与全A宽度获取失败 | CI中第三方HTTP接口断连；不可假设所有API均可用 | 指数改用AKShare新浪 `stock_zh_index_daily` 备选；宽度仍明确 FAILED | [成功读取指数的run 40684116228](../../records/2026-10-28/close/40684116228-a1.json) |
| 2026-10-28 | 大量快速push时旧版本CI被取消 | 新版本推送，串行Actions/竞争导致排队旧任务退出 | 只把精确匹配最终代码 SHA 的成功CI用作验收 | [实际运行时间线](../indices/runs.md) |

**纠错纪律**：原始“交易日历导致TypeError”的假设是错误诊断，证据推翻后必须保留本条并注明改正。不能为包装成功删掉失误。

**尚未解决**：全A市场宽度、部分两融/ETF份额与NAV、分钟14:50卖出、点时股票池缺失。见 [开放问题](../open-questions.md)。
