---
id: EXP-0016
type: experiment
status: active
updated: 2026-11-03
---

# EXP-0016：V5调度时效修复——完成触发，禁止倒签

**动机：** 11月2日计划的盘后流水线被GitHub Actions `schedule` 推迟约十小时。V3原定17:25（北京时间）→11月3日03:35:57启动、03:37:04结束（[run 41511425563](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41511425563)）；V5原定18:05→次日04:02:08启动（[41515451702](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41515451702)）；模拟盘跟踪原定18:45→次日04:29:49启动（[41519712835](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41519712835)）。原V5新资金事件于次日04:05冻结，`intended_session=2026-11-04`；11月3日三模拟账户均为现金。

**本轮基线主分支SHA：** `f684891dde19672e2cff27b18a76ce0efb4a696c`。假设：将独立cron串为`V3成功→V5成功→收益账本`，同时保留原cron兜底，可缩短**上游作业完成至下游启动的额外排队**，不需要改变基金数据、选股排序和证券时点。

## 实施边界

1. V3仍按17:25工作日盘后跑；成功完成后自动触发原V5事件路由。V5成功完成（含不可覆盖的推送归档）后立即触发原收益跟踪和三组账户。每个原cron继续作为独立兜底，`workflow_dispatch`照旧。
2. 下游只在上游`conclusion=success`且`main`分支触发，避免失败/取消任务生成新纸面记录。使用原本的`concurrency`与事件日去重机制，防止双触发重复冻结；每次记录仍以不可覆盖run ID命名。
3. 三条工作流在运行日志和Step Summary标注基于UTC cron/上游结束时间的真实延迟分钟；超过60分钟打印非阻断警告。**告警不是删掉机会的风控开关。** `schedule`晚来仍如实运行，只会如实记录时点。
4. **不改** `run_national_team_left_entry_v5.py`、`next_weekday`、`paper_account_v5.advance`、任何`records/`或既有`intended_session`。已冻结2026-11-03事件的拟入场仍是2026-11-04；缺价格或已经错过的机会继续显示未成交，不补单。
5. 根因中GitHub自身的`schedule`启动延迟并不因workflow_run消失。新链只消除各下游独立等待；若V3仍晚到次日，记录`DELAYED`并评估增加仓库外可靠调度入口，**不能把预定时间假装实际执行时间**。

## 验收与失败门槛

- 静态/单测：两级`workflow_run`工作流名准确、`completed`成功门槛、生效分支、cron保留、对真实11/02启动时间计算10小时级延迟、2026-11-03旧拟入场日仍为11/04。
- 实跑：合并后确认在**上游V3成功的同一工作日**有`workflow_run`触发的V5，V5成功后有`workflow_run`触发的模拟盘；每次必须核实Action事件、作业SHA、时间和独立JSON，不能只看配置。
- 衡量：`upstream_completed_at → downstream start`分钟；目标常态≤10分钟，超过60分钟触发告警。V3实际cron偏离目标≤30分钟为外部基础设施指标；若再现10小时延迟，EXP-0016视为**只修复了串联，没有解决根触发时效**，需切换可靠外部定时源。
- 任何旧交易历史倒签、基于过往开盘价回填模拟买点、新增券商权限均为直接失败。

关联：[根MOC](../../MOC.md) · [三账户纸面规则](EXP-0014-v5-paper-account.md) · [事件路由](../../.github/workflows/national-team-event-router-v5.yml) · [收益工作流](../../.github/workflows/national-team-left-outcomes-v5.yml)。

## 2026-11-03 合并后实际链路验收

**合并后真实验收（2026-11-03，北京时间09:21—09:23）：** [主分支合并SHA b926992](https://github.com/lican1213/a-share-momentum-runner/commit/b926992fe124918670db3757a75470265c6c2b2c)；[PR #8 全库CI #41558977738](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41558977738)及[main全库CI #41559156956](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41559156956)成功，**282 passed + Wiki链接校验PASS**。[V3 #41559156926](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41559156926) 于UTC01:21:49完成后，[V5 #41559251512](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41559251512) 于01:21:52被`workflow_run`实际触发（**3秒**）；该V5在UTC01:22:23完成后，[模拟盘 #41559316107](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41559316107)于01:22:26触发（**3秒**）且两者均SUCCESS。新路由[原件](../../records/national_team_router/2026-11-03/41559251512-a1.json)为`ALREADY_FROZEN_FOR_SESSION`，没有重冻；[新模拟账户原件](../../records/national_team_paper_accounts_v5/2026-11-03/41559316107-a1.json)仍为各30,000元现金、0持仓、0平仓、0券商单。**完成触发链已实际证实；GitHub下个正常工作日晚间定时是否准时尚未证实。**
