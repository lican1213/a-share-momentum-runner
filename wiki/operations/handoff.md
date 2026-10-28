---
id: OPS-HANDOFF
type: operations
status: active
updated: 2026-10-28
---
# 新Agent上手与交接：最短可复现路径

## 15分钟阅读顺序
1. [根MOC](../../MOC.md) 和 [AGENTS](../../AGENTS.md)；
2. [一页研究状态](../compiled/briefing.md)、[模型台账](../models/registry.md)；
3. [源证据索引](../indices/runs.md) → 最新成功的 `records/` 文件，检查run ID/commit SHA与数据源；
4. [EXP-0001](../experiments/EXP-0001-baseline.md)、[EXP-0002](../experiments/EXP-0002-regime.md)、[事故史](../incidents/INC-0001-bootstrapping.md)；
5. [发行门槛](https://github.com/lican1213/a-share-momentum-runner/issues/1) 与 [研究待办](https://github.com/lican1213/a-share-momentum-runner/issues/2)。

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
