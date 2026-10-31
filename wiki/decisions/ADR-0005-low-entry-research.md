---
id: ADR-0005
type: decision
status: active
updated: 2026-10-31
---
# ADR-0005｜原始四ETF资金指标主导“下跌途中左侧跟随”研究

## 决策背景

2026-10-31用户再次明确：项目的价值是**追踪国家队相关资金动向，在市场尚未止跌时尝试跟随并获取有限反弹收益**。2026-10-27最初设定的四ETF份额/NAV资金因子，就是用户认为最接近国家队入场行为的公开先行指标，不应被“10日突破＋放量”的短线动量模型取代。

10月30日A2严格组筛出的601919中远海控、601166兴业银行，5交易日已经分别上涨约12.56%和6.97%。这说明A2选择的是相对强势、已发生价格反应的股票，**和用户要求的更早、更低位、跟随宽基逆势资金承接存在目标错位**。能否随后继续涨与它是否是低位建仓机会属于不同问题。

## 研究方向决策（仅协议，不实施）

1. **坚持原始资金序列**：核心四只510300、510310、510330、159919日份额变化×对应NAV、五日强度、规模及普通/自由流通分母完整保留；扩展9/23ETF只做横向一致性和轮动验证，不改变原序列。原3%是假设预警，不凭这两周行情优化出“国家队入场准确率”。
2. **逆势而非追突破**：先找“ETF净申购持续正值，同时沪深300还在下跌/回撤”的真实首次公开事件，再研究相关沪深300成分股的“相对抗跌、绝对尚未大涨”与左侧买入时机。不要以MA60/10日突破/量比强制筛掉市场仍在下跌时的早期承接。
3. **保留真实资金与归因边界**：ETF份额是真实全体持有人净申赎代理；汇金、证金、诚通、国新等账户持仓仅法定披露才确认为法人持仓。可把四ETF作为疑似大机构/稳市方向的研究触发器，但不可写成“国家队当天买了某股”“国家队下周几拉升”。PCF/实物申赎亦不保证股票同日二级市场买入。
4. **正面对抗“接飞刀”**：设置F1直接左侧试验、F2等待最多3个交易日弱企稳再介入，严格记录跌破、跳空、不可成交、T+1、止损和留现金，不用未来最低价挑胜场。若不能跑赢同日起买ETF，则承认买ETF更简单。
5. **不改写旧实验**：EXP-0004、EXP-0005-A2、EXP-0006、原2026-10-28/30不可回写冻结及执行器、已有损益/错误记录保持原状；新方向以[EXP-0007计划](../experiments/EXP-0007-flow-absorption-low-entry-plan.md)独立命名、建立未来记录。当前状态PLAN_ONLY、RESEARCH_ONLY、无实盘授权。
6. **科学判定**：未来真实资金事件后5/10/20日，费用后的F1/F2要同时对比同起点510300ETF、旧突破模型和同市场状态下未用资金触发的普通抗跌滞涨股组；若没有增量价值，记录负证据并停止“调参调出盈利”。

## 参考开源方法的选择

- 资金/持仓双时钟：[kitaki-Ciallo/etf-national-tracker](https://github.com/kitaki-Ciallo/etf-national-tracker)；[wwww1998/national-team-etf-flow](https://github.com/wwww1998/national-team-etf-flow)。
- 下跌干预和价格底不同：[zoeyzhu97/etf-monitor](https://github.com/zoeyzhu97/etf-monitor/blob/main/MODEL_ASSESSMENT_REPORT.md)。
- A股T+1与事件回放：[ricequant/rqalpha](https://github.com/ricequant/rqalpha)；数据复权和中国市场基线：[microsoft/qlib](https://github.com/microsoft/qlib)；研究事前冻结与成熟再评：[PanGucheng/a-share-quant-research](https://github.com/PanGucheng/a-share-quant-research)。
- 不接受任何开源项目将全ETF份额直接标为汇金逐日持仓，也不照搬未经验证的盈利率、证书校验绕过或样本内最优参数。详细逐项目借鉴/拒绝项见[EXP-0007](../experiments/EXP-0007-flow-absorption-low-entry-plan.md#3-严格对照的github项目借什么拒绝什么)。

## 与旧决策的关系

此ADR是[ADR-0003国家队主线](ADR-0003-national-team-pivot.md)与[ADR-0004资金转股票](ADR-0004-stock-selection-after-flow.md)的**研究取向补充**，不是覆盖旧文档，也不是软件上线声明。

**下一实现Gate**：冻结EXP-0007预注册协议、验证2026-10-31基线SHA、补时间戳/拆分/历史成分来源，再建独立F1/F2；未通过证据与费用后收益验证，保持 RESEARCH_ONLY_NOT_TRADE_AUTHORIZED。
