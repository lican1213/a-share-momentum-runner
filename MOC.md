# MOC — 国家队资金跟踪与跟随收益研究第二大脑

## 2026-10-29 EXP-0005：短线一周严格纸面试验（尚未有可信成交或收益）

- **[已冻结试验协议](wiki/experiments/EXP-0005-national-team-one-week-paper-pilot.md)**：2026-10-29午间冻结；3万元模拟账户、最多1万元首批投入、S1/S2各最多一只、100股整数手、单笔初始含成本风险≤150元；不许用2026-10-29已过去的09:30回填买入。V2原5/10/20交易日研究保持独立。
- **[专用纸面试验程序](national_team/short_paper_pilot.py)**、[定时执行任务](.github/workflows/national-team-short-paper-week.yml)及[对抗测试](tests/test_national_team_short_pilot.py)：从确认行情计算MA/突破/ATR、价格与整数手约束，情景性次交易日开盘入场，T+1至T+3固定出场规则，14:50必须有分钟行情才能记时间退出，和510300同起点对照；GitHub Actions工作日18:15采集并试图保存不可回写审计记录。**文件已部署≠Actions实际运行/真实行情抓取/买入成功**，查证最新run、提交SHA及freeze记录后才可宣称启动。
- **初始状态**：0笔经核验的纸面成交、0笔真实成交、0元已证明收益；如果2026-10-29 17:30后冻结失败，就不得2026-10-30回填。2026-11-05晚间仅依据已持久化来源和真实已执行程序作阶段结论。

## 2026-10-29 B17 修复与验收进度

- **V2日报与V1历史分栏**：[报告编译代码](national_team/daily_report.py)从首次不可回写V2事件及对应策略JSON恢复S1/S2，避免将旧版V1 S2误当主模型；[最新日报](wiki/compiled/national_team_daily.md)已通过真实Wiki生成任务，显示V2 S2为600309/601919/600660/601012/601838，旧版600000/601816/601166/600519/000333单列历史。
- **成交情景修复**：[OHLC审慎过滤](national_team/ohlc_execution_guard.py)与[实际行情接入](national_team/live_paper_tracker.py)：此前仅依日成交量假设能按开盘价买/卖的缺陷，改为读取高低价、上一交易日收盘价；出现疑似一字涨停/跌停则按不可成交处理，并保留每条记录仅为OHLC情景、非真实券商成交的证据。
- **资金源改进**：[ETF采集](national_team/live_etf_sources.py)对上交所HTTP403启用本轮熔断，缩减无效重试，并增加按具体交易日的AKShare SSE后备采集；逐基金/日期保留来源哈希与冲突记录，不用未知份额填充。没有稳定的官方PCF、全部日期SSE/SZSE网络可达性尚不可被单元测试替代。
- **披露时点纠正**：[ETF定时采集](.github/workflows/national-team-live.yml)调整为北京时间每周二至周六09:15、[V2冻结](.github/workflows/national-team-strategy-v2.yml)调整为10:15，避免在官方每日份额未公布前将缺数误当新交易信号。源更新通常在T+1上午，见[Tushare数据文档](https://tushare.pro/document/2?doc_id=408)；具体日期必须依真实归档确认。
- **工程测试不是收益验证**：[118项通过的CI 40787840541](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40787840541)已覆盖V2日报分流等回归，独立实盘成交和扣成本超额收益仍为OPEN。新增[二级份额规范化器](national_team/tushare_share_fallback.py)仅为待授权数据接口的单元适配基础，**尚未接入生产，绝不报告为已取得Tushare数据**。



**Agent starts here.** [操作规则](KNOWLEDGE.md) · [AGENTS入口](AGENTS.md) · [Wiki总索引](wiki/index.md) · [一页当前状态](wiki/compiled/briefing.md)

## B16：真实四ETF资金驱动的独立选股V2首次运行成功（2026-10-28）

- **[V2真实Github运行40719359363](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40719359363)成功**：18项策略/评价对抗测试，2026-10-27完整四ETF真实净申赎代理+56.12亿元，2026-10-28实际150只股票样本（覆盖83.015%），同一数据源生成新版本两个前瞻冻结股票组合；源码 [strategy_v2.py](national_team/strategy_v2.py)，[EXP-0004完整协议](wiki/experiments/EXP-0004-four-etf-strategy-v2.md)。
- **[首次策略原始JSON](records/national_team_strategy/2026-10-28/40719359363-a1-v2.json)**、[两组首次冻结事件](records/national_team_events/2026-10-28/40719359363-a1-v2.json)：S1为601825/600000/601229/601166/600519；独立S2为600309/601919/600660/601012/601838。冻结首次可用策略时点2026-10-28 23:46（北京时间），资金底层交易日不是股票成交日。V2有[自动每日运行及Git原件归档](.github/workflows/national-team-strategy-v2.yml)。
- **结构限制必须传给后续Agent**：四ETF若仅用同一个CSI300权重代理，资金规模不会影响股票横截面排序，**ETF净申赎仅充当时间触发器**。真实PCF、2026法人主体身份与5/10/20日S1/S2相对直接持有510300的净超额收益还没有证实，真实交易授权依旧OFF。

## B14 最新事实：真实生产链路通过，旧汇金持仓被新总份额证伪

- **[真实生产通过 run 40710985962](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40710985962)**：150股真实OHLC/ADV20，资金来源合并、S1/S2冻结校验、独立红队`RESEARCH_PRIOR_FOUR_CURRENT_PARTIAL_AUDITED`及**`ETF_SOURCE_RECORD_PERSISTED`写回全部成功；先前连续`cancelled`与Wiki同提交rebase冲突/未暂存文件失败已修复并列入测试。
- **[每日可读研究简报](wiki/compiled/national_team_daily.md)** 与[原始B14版本](records/national_team_daily/2026-10-28/40710985962-a1-v4.json)：10月27日完整四ETF+56.12亿元；10月28日仅沪市三ETF+16.71亿元（不混日）；股票150只、83.02%指数权重覆盖；S1/S2保持第一次冻结候选，尚未成熟净超额收益。
- **身份红队关键证伪**：2025年6月30日159919两家汇金法人合计持有354.98494985亿份，但[2026年6月30日整个基金总份额](data/national_team_holders/159919-2026H1-fund-total.json)仅约69.39216676亿份；**2025历史持仓不能延续为2026年有效仓位判断**。请独立核对份额折算与2026报告具体法人持仓，不能凭整个ETF份额变化证明某个国家队账户哪天卖出。身份一致性[测试](tests/test_national_team_stale_holder_total.py)与[日报模块](national_team/daily_report.py)已接入。
- 本轮`CI`和Wiki版本都真实验证。**实际ETF PCF仍未获取有效可核对明细**，股票映射仍是指数权重代理；5/10/20交易日样本外股票超额收益未验证，所以策略不标已盈利。

## B13 当前交付：不可回写证据→国家队身份→每日股票策略简报

**[B13对抗审计](wiki/audits/AUD-2026-10-28-e2e-release-gate.md)** · [持有人证据：159919的2024/2025中报](data/national_team_holders/159919-2024H1-2025H1.json) · [持仓变化校验](national_team/holder_evidence.py) · [资金与个股研究简报生成器](national_team/daily_report.py) · [原始运行证据与派生Wiki分离的任务](.github/workflows/national-team-wiki-sync.yml)。

真实股票研究已覆盖150只沪深300成分股（约83.015%的指数权重），两条S1/S2前瞻观察名单已经冻结，但5/10/20交易日尚未成熟。法定持仓已独立建立159919的2024/2025基线，**不能代替2026持仓和当日账户交易**。研究源/归因通过历史红队重放；最近生产运行曾因Wiki自动摘要同仓rebase冲突失败，现已经把不可变证据与派生索引分开，仍须匹配新完整生产run验收。**策略盈利没有获得可宣称的样本外正结果**。

## B11—B12 当前进展：真实四ETF → 股票候选 → 独立审计

**[E2E审计报告](wiki/audits/AUD-2026-10-28-e2e-release-gate.md)** · [四ETF真实来源](records/national_team_etf/2026-10-28/40702172792-a1.json) · [跨运行完整资金快照](records/national_team_merged/2026-10-28/40702572594-a1.json) · [30只真实股票观察排名](records/national_team_watch/2026-10-28/40702172792-a1.json) · [完整量化CI](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-factors.yml) · [最新源采集Actions](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-live.yml)

**已完成**：四只固定沪深300ETF的交易日份额及NAV、日/5日资金指标、SSE/SZSE相互备份与多run合并、CSI300正式指数权重及实际股票ADV20研究排名、S1/S2候选冻结与5/10/20日纸面评价器、基于真实落盘数据的独立红队重算及篡改失败测试。公开持仓身份与ETF实际PCF尚未贯通；当前股票排名是**指数权重研究代理**，不是国家队逐股订单。独立样本外盈利能力仍未得到验证。

**已完成B12**：[真实综合运行40706300084](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40706300084)已成功生成150只股票研究排名（覆盖CSI300权重83.015%）、2026-10-28三沪ETF最新资金代理、两条冻结S1/S2纸面事件及独立审计留档。**最新10月28日缺159919**，最近完整四ETF为10月27日；双日期保留修复在[81项对抗回归CI 40707718330](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40707718330)通过。完成的旧版运行不能替代新修复的综合生产验证。新[带超时SSE原始接口](national_team/sse_direct.py)已部署。

## 研究纪律纠偏：主动发现机会，不让数据缺口清空研究名单
**[研究主扫描器 opportunity_scan.py](national_team/opportunity_scan.py)**：已核实的部分ETF篮子、个股数据可以继续排序，完整列出覆盖比例与风险标签；资金净流出也产生撤退风险名单。停牌/ST等已明确不可交易者单列。历史上过于严格的[stock_selection.py](national_team/stock_selection.py)保留为全量证据审计版而非唯一研究入口。真正实盘订单另行验证，不阻断研究输出。

## 2026-10-28 对抗式审计结论与真实行情落地
**[P0/P1审计完整报告](wiki/audits/AUD-2026-10-28-red-team.md)** · **[真实ETF数据采集器](national_team/live_etf_sources.py)** · **[真实数据运行日志](https://github.com/lican1213/a-share-momentum-runner/actions/workflows/national-team-live.yml)** · **[前瞻配对收益计算](national_team/forward_evaluation.py)**

**阶段结论已由B11更新**：独立深交所按日期JSON接口已取得159919历史份额，四ETF份额/NAV和资金指标已真实计算；但国家队本人持仓核验、ETF真实PCF、成本后独立超额收益仍未完成。以顶部E2E审计和run证据为准。

## P0 策略核心：资金信号后如何选股、是否跑赢买ETF
**[ADR-0004 资金→股票映射与ETF基准](wiki/decisions/ADR-0004-stock-selection-after-flow.md)** · **[EXP-0003 S0 ETF基准 vs S1资金冲击 vs S2相对强度](wiki/experiments/EXP-0003-etf-to-stock.md)** · **[研究代码](national_team/stock_selection.py)**

**国家队资金进出指标是触发器，不是最终交易策略。** 从核心四ETF份额变化和披露持仓出发，按当时PCF/成分权重映射到股票，比较股票20日成交额与相对强度；最关键的盈利证据是公开信号之后5/10/20交易日是否持续跑赢低成本沪深300ETF。股票真实日线与指数权重代理排名已取得，但不能将其称为ETF真实PCF对应买单，也不能据此断言已经跑赢ETF。

## P0 原始四ETF入金/出金指标 + 国家队持仓联合追踪（2026-10-28恢复）
**[原始四ETF资金指标、5日强度及双市值覆盖率](wiki/data/original-four-etf-indicator.md)** · **[指标Python实现](national_team/core_flow_factors.py)** · **[ADR-0003整合决策](wiki/decisions/ADR-0003-national-team-pivot.md)**

原指标固定510300、510310、510330、159919；扩展九ETF作为横向比较，中央汇金等持有人披露用于低频身份确认，大盘状态用于风险过滤。**不能把ETF总净申购算成汇金当日买入。** 原三日追涨仅作旧实验，不是模型中心。

## P0 现行唯一主线（2026-10-28明确纠偏）
**[ADR-0003 国家队跟踪重定向](wiki/decisions/ADR-0003-national-team-pivot.md)** · **[国家队ETF官方数据MVP Issue #3](https://github.com/lican1213/a-share-momentum-runner/issues/3)**

**主要目标：从公开披露确认国家队主体持仓、监测相关ETF的实际份额净申赎，研究在信号首次公开可得之后跟随能否盈利。**

原三日突破策略、45笔历史回放、H01研究全部作为**旧实验/历史证据**保留，不再是主线，停止无目的优化。ETF份额流入只能说明该ETF全市场净申购，不能直接声称中央汇金当天买入。无经核验的真实交易数据则不发可执行指令。

## 1. 当前项目与安全边界
- [当前结论 / 研究架构](wiki/overview.md)
- [模型版本台账及状态](wiki/models/registry.md)
- [当前重大未完成问题](wiki/open-questions.md)
- [发布门槛 Issue #1](https://github.com/lican1213/a-share-momentum-runner/issues/1) · [改善路线 Issue #2](https://github.com/lican1213/a-share-momentum-runner/issues/2)

## 2. 证据与复现
- [运行记录自动索引](wiki/indices/runs.md)（按实际 `records/` 重建）
- [代码提交索引](wiki/indices/commits.md)（按 Git 提交重建）
- [数据口径、时间戳、成交假设](wiki/data/contracts.md)
- [原始逐次运行 JSON](records/) · [GitHub Actions](https://github.com/lican1213/a-share-momentum-runner/actions)
- [数据源 / 项目参考](wiki/sources/catalog.md)

## 3. 研究、升级与失败
- [EXP-0001 原始三日策略与退出归因](wiki/experiments/EXP-0001-baseline.md)
- [EXP-0002 H01 双指数趋势过滤](wiki/experiments/EXP-0002-regime.md)
- [ADR-0001 Research-only 决策](wiki/decisions/ADR-0001-no-trade.md)
- [ADR-0002 数据证据与失败关闭](wiki/decisions/ADR-0002-evidence.md)
- [INC-0001 初次部署、403、接口与QuantStats错误](wiki/incidents/INC-0001-bootstrapping.md)
- [CTR-0001 被证伪的原因诊断与相互矛盾的结论](wiki/contradictions/CTR-0001.md)
- [维护时间日志](wiki/log.md)

## 4. 后续Agent操作
- [交接指南（接手必读）](wiki/operations/handoff.md)
- [MOC/Wiki维护规范](KNOWLEDGE.md)
- [Claude Code入口](CLAUDE.md) · [Gemini CLI入口](GEMINI.md) · [GitHub Copilot入口](.github/copilot-instructions.md)
- [实验模板](wiki/templates/experiment.md) · [决策模板](wiki/templates/decision.md)
- [GitHub连接器部署Skill](skills/github-connector-write-deploy/SKILL.md)
- `python scripts/wiki_lint.py` 与 `python -m pytest -q`

**当次记录可审计 ≠ 模型有效 ≠ 实盘交易已执行。** 最近可核实的研究性运行： [run 40685553957](records/2026-10-28/close/40685553957-a1.json)，16项测试通过；45笔基于真实行情的**假设成交回放**仍为负期望，H01过滤后也仍为负。当前仓库没有任何已授权的可执行买点。
