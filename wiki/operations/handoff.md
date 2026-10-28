---
id: OPS-HANDOFF
type: operations
status: active
updated: 2026-10-28
---
# 新Agent上手与交接：最短可复现路径

## 当前主要项目（旧三日动量不再是主线）

1. [MOC](../../MOC.md) → [B11/E2E红队审计](../audits/AUD-2026-10-28-e2e-release-gate.md) → [四ETF真实资金记录](../../records/national_team_etf/2026-10-28/40702172792-a1.json) → [真实股票指数代理观察名单](../../records/national_team_watch/2026-10-28/40702172792-a1.json)。
2. 资金指标用[core_flow_factors.py](../../national_team/core_flow_factors.py)、[szse_json.py](../../national_team/szse_json.py)、[sse_direct.py](../../national_team/sse_direct.py)、[record_merge.py](../../national_team/record_merge.py)；股票、纸面评价与审计用 [live_stock_watch.py](../../national_team/live_stock_watch.py)、[paper_events.py](../../national_team/paper_events.py)、[live_paper_tracker.py](../../national_team/live_paper_tracker.py)、[audit_gate.py](../../national_team/audit_gate.py)。
3. 最新正式Actions见[国家队真实采集](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-live.yml)与[独立单元审计](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-factors.yml)。复核精确代码SHA、完整源记录、红队状态、连续交易日，不能只看绿色workflow。
4. 先证明资金源与选股排名准确，再评价5/10/20日S0 ETF基准、S1和S2股票组合；当前只有OHLC模拟评价接口、没有稳定正超额收益证据。PCF与中央汇金真实持仓仍需另行取得。

## 15分钟阅读顺序
1. [根MOC](../../MOC.md) 和 [AGENTS](../../AGENTS.md)；
2. [一页研究状态](../compiled/briefing.md)、[模型台账](../models/registry.md)；
3. [源证据索引](../indices/runs.md) → 最新成功的 `records/` 文件，检查run ID/commit SHA与数据源；
4. [EXP-0003资金→成分股](../experiments/EXP-0003-etf-to-stock.md)、[最新E2E红队审计](../audits/AUD-2026-10-28-e2e-release-gate.md)、[事故史](../incidents/INC-0001-bootstrapping.md)；EXP-0001/0002为旧三日突破历史支线；
5. [当前国家队P0策略任务](https://github.com/lican1213/a-share-momentum-runner/issues/3)；旧Issue1/2仅作历史。

## 安全执行检查
```bash
python -m pip install -r requirements.txt
python scripts/wiki_lint.py
python -m pytest -q
python runner.py --phase close --out output
```
线上实际运行以 [GitHub Actions](https://github.com/lican1213/a-share-momentum-runner/actions) 的run结论及 `records/` 为准。盘前/午间与push触发的close测试不同。

检查：市场交易日→当期日K是否到齐→数据哈希/时间戳→测试成功与否→AKQuant仅API smoke→逐笔回放估计值→市场宽度与分时数据缺口→研究态授权开关。

## 变更怎么记
- **纯说明修订**：改对应Wiki主题、`wiki/log.md`、MOC/索引如必要；提交明确说明原因。
- **行情/回测逻辑变化**：先建一页EXP（没有数据则`status:unverified`）与研究假设，再改代码并补测试；标明旧SHA/新SHA、参数/数据差异、失败日志和实验结果；更新[版本登记](../models/registry.md)与日志。
- **权限、数据、API、依赖事故**：开/更新 INC，引用失败run和修复run，保存被证伪的初始猜测；核对上游仓库接口。
- **改动交易授权门槛**：新增ADR并完成独立样本外验证+用户明确授权，否则保持0个正式信号。
- **新研究结论**：附证据在主题页，记下局限；若跟旧结论矛盾，显式写“superseded by evidence”，不要覆盖原始 `records/`。

## 交接输出最低格式
`截至YYYY-MM-DD, branch/main HEAD=..., latest successful Actions=..., audited data asof=..., current strategy version=..., authorization=OFF, this turn changed ..., tests=..., unresolved blockers=..., next recommended single experiment=...`

## 禁止
不能引用尚未结束的CI证明“运行通过”；不能把PR/文档中的收益当成本仓库回测；不能对已看过的45笔调参然后号称严格OOS；不能自动接入券商。
