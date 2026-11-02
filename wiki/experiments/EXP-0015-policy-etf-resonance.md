---
id: EXP-0015
type: experiment
status: active
updated: 2026-11-02
---

# EXP-0015：官方政策 × 四ETF逆势申购的资金共振增强层

## 本轮决定与冻结假设

**假设：** 同样是下跌日四ETF逆势净申购，最近七个自然日内有一手、可在当时观察到的资本市场稳市政策，比无匹配政策的事件更可能形成随后3/5/10个交易日的净超额。此为待验证的事件分组，不是新的自动券商开关、主覆盖率替代品或已经成立的60%胜率。

- **基线：** 2026-11-02主干树 d5ef599acb9d9f726b308564e9a1474286c524c9；V5 / EXP-0012、0013、0014现金账户交易逻辑完全不改。
- **触发不改：** 固定 510300/510310/510330/159919；ETF_AUM/沪深300普通流通市值仍为核心指标（缺真实官方分母为NULL），份额×NAV净申购代理触发原V5下跌日事件。
- **唯一新增：** 官方公告采集、同一事件按标题归并、政策层级标签、关联ETF资金交易日，并在不可覆盖的路由和模拟入场冻结记录中保存研究标签。政策不单独发券商单，也不拒绝本已合格的低位纸面试错。

## 参考项目：只借精简机制

1. [KKKKhazix/AIHOT](https://github.com/KKKKhazix/AIHOT) 的 [信源文档](https://github.com/KKKKhazix/AIHOT/blob/main/docs/sources.md) 提供 RSS/网页/JSON 多类型、T1信源分层、事件去重和采集状态的范式；我们只吸收 T1官方来源、同事件合并、独立源故障可见、正文含时点，不引入 Postgres/Node/LLM打分/热点站。
2. [YangSal/ashares_data_collect](https://github.com/YangSal/ashares_data_collect/blob/main/data_collect/jobs/news_regulator_current.py) 的中国证监会 JSON 当前接口、国务院政策文件库 JSON 查询结构经过开源项目使用；我们独立用 Python 标准库适配当前字段。
3. [中国人民银行新闻RSS](http://www.pbc.gov.cn/goutongjiaoliu/113456/2986536/index.html)、[证监会官方动态](https://www.csrc.gov.cn/csrc/c100028/common_xq_list.shtml?tab=02)、[国务院政策文件库](https://sousuo.www.gov.cn/zcwjk/) 是一手出处。官方新闻或政策文件是政策事实证据，不是实际ETF资金已经买入的证据。

## 实际采集 / 不可覆盖记录

在原 [18:05 事件工作流](../../.github/workflows/national-team-event-router-v5.yml) 内，先运行 [collect_national_team_policy.py](../../scripts/collect_national_team_policy.py)，不添加另一个 cron 和执行器；三源抓取后由 [policy_overlay.py](../../national_team/policy_overlay.py) 处理：

| 源 | 接入 | 实际字段及时间语义 |
| --- | --- | --- |
| PBC_RSS | 央行新闻 RSS/Atom XML | 官方原文标题、URL、pubDate；无RSS/断连则标源失败 |
| CSRC_NEWS | 官方搜索 JSON searchList/a1a078ee... | publishedTimeStr、标题、原文链接、文章摘要；时间转北京时间 |
| GOV_POLICY | 官方政策库 JSON search-gov/data | pubtimeStr（只有日期）、标题、摘要、原文链接；日期不伪装为精确的盘中发布时间 |

- 每个源记录成功/失败、原始条数、政策相关条数和可读错误。某源断连不使四ETF资金事件被过滤；三源全失败时只报 POLICY_SOURCES_UNAVAILABLE，不捏造“没有政策”。
- 只保留资本市场稳市/中长期资金、降准降息等宽松、明确收紧、产业政策等可追踪标签；同标题跨来源合为一个政策事件，并保留原文链接。
- 记录 published_date、精确时间（若有）、publication_precision、first_observed_at_bj 和采集源快照SHA。首次采集时间从历史不可覆盖文件恢复，不允许今天才看到的旧公告回填成过去某次已冻结的预测输入。
- 路由用 [发布于当前资金日之前/当天] ∩ [近7天] ∩ [本次首次观察已发生] 判断 POLICY_ETF_RESONANCE，同时保留仅政策无资金、仅资金无政策的反事实组。事件日之后公布的政策不能倒填为当天资金入场原因。
- 归档 records/national_team_policy/YYYY-MM-DD/RUN-aATTEMPT.json，路由 records/national_team_router/ 同 run 一对一保存 policy_overlay；发生新V5冻结时 records/national_team_left_entry_v5/ 保存当时政策标签和对应路由SHA；三组 EXP-0014 现金、持仓、订单、成本和T+1/T+2不改。

## 后续独立验收与晋升条件

- **软件：** 多源同事件去重、失联、时间在未来、仅日期发布时间、政策先于/后于资金交易日、无政策也继续产生原V5买入研究、券商授权仍false、历史first-seen恢复；必须全库测试和Wiki校验。
- **真实源：** 18:05工作流完成、三源逐项日志、真实官方原文/时间可读；按run-a原样落盘。所有source失败时也保留当日诊断，而不是任务悄悄绿色就称已采集成功。
- **收益：** 按已经冻结的ETF事件簇唯一性关联后续 EXP-0014 的三组纸面账本和 EXP-0013 3/5/10日MFE/MAE，报告 POLICY_ETF_RESONANCE、ETF_FLOW_WITHOUT_POLICY_MATCH、POLICY_WATCH_WITHOUT_ETF_FLOW 三组的胜率、扣费净利润、相对510300超额及最大回撤；同一政策、连续资金日不当作独立多次胜率。
- **失败条件：** 无足够独立成熟资金簇、公告时间晚于交易时点、政策并没有增加扣费超额、负例回撤恶化，则政策继续只当标签，不自动改变真实/纸面准入阈值。后续达到足够样本，再单独冻结是否将政策强度作为候选排序加分实验。
