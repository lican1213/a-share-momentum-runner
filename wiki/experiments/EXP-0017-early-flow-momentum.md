---
id: EXP-0017
type: experiment
status: active
updated: 2026-11-17
---
# EXP-0017：大额资金早期信号与主动追涨
基线 2ebfab0b61d07f2f63cd23397c79a3769e0798af。用户明确鼓励短线追涨而非仅等待低位反弹。借鉴 [Resonance](https://github.com/OrangesHuang/Resonance) 多信号共振与降级，[A-ETF-Analysis](https://github.com/charleslau1988/A-ETF-Analysis) 建仓早期/加速状态，[Ponytail](https://github.com/DietrichGebert/ponytail) 最小改动。仅复用公开说明中的设计，不复制其依赖或声称复现收益。

- 四ETF主指标及原标准资金条件不改。下跌环境完整四ETF单日净申购代理达到50亿元时，允许独立早期模拟，不等待五日累计确认；标 EARLY_ONLY/ STANDARD_AND_EARLY，代理不升格为官方身份或交易所确认。日期匹配、真实行情、去重和三自然日时效仍适用。
- EARLY_ENTRY 新独立30,000元账户，复用两只股票/每组最多10,000元毛额、单股5,000元及150元计划止损风险预算，不新增引擎。排序使用20日低点距离、相对强度和五日正涨幅的已有信号票数；没有融资/60日/分钟数据不伪造。R_BOUNCE 对完整已验证股票池按正绝对/相对五日收益排序，不限3%，高追涨风险保留标签。SHALLOW/DEEP继续按原标准资金条件入场。
- 北京时间09:15之前完成合法冻结且信号属于较早交易日，可计划当日真实交易所开盘；此后才冻结则下个交易日。只在现有日线情景执行，不补买；无同日股票数据仍等真实源。
- 旧三组状态迁移保留，旧记录不改写。旧R_BOUNCE仅历史定义，EXP-0017以策略实验ID分开统计，3/10日按独立成熟资金簇和同期S0费后超额，未到期不计。连续账本仍保留T+1以后±3%及T+2收盘代理。
- 阶段二：用新的实际纸面净超额验证预算/信号，而非凭空指定最优权重；阶段三：至少8个独立同事件成熟配对簇并检查三日实现净超额后才考虑纳入自动默认选优，现有左右账户均主动模拟但旧左侧自动比较不改。未来新增仓位或自动策略升级必须单独预注册，不把新旧R历史混作胜率。
- G0: 运行匹配SHA全库测试/Wiki校验；G1: 实源新路由/冻结且合法抢早；G2: 四账户实际新归档并核对旧现金、持仓、历史；G3: 成熟收益，明确NULL。代码已在PR #22主链合并，PR #23修正真实生产缺失日历依赖。G0同SHA全库软件验证PASS；G2实际四账户迁移/写入PASS；G1下一新资金事件的EARLY_ENTRY及追涨入场和11/18原6笔订单仍待真实首次开盘/后续归档；G3扣费后净超额和成熟簇尚未验证。08:30/12:30/17:30条件监测和所有原cron不变；零真实券商交易。

红队补充：每组在同一资金簇首次存在候选时即锁定观察单元，早期未成熟/缺行情时不得替换为簇内后续已盈利事件；记录与浅跌组不同股票且同事件成熟的配对差，避免混算旧R收益。早期独立冻结后按原交易日去重，不再对同资金日补标准订单；早期独有样本只与S0比较，不能算左右组共同配对。

## 2026-11-17 实跑验收与边界
- 原始EXP-0017 [PR #22](https://github.com/lican1213/a-share-momentum-runner/pull/22) 经328项全库测试合并；首次[生产账本run #44061324220](https://github.com/lican1213/a-share-momentum-runner/actions/runs/44061324220) **失败**：工作流未装原路由已有`exchange-calendars`依赖，新增盘前日历测试在实际执行前报`ModuleNotFoundError`。没有归档成功，不冒充验收。
- [PR #23](https://github.com/lican1213/a-share-momentum-runner/pull/23)沿用路由锁定版本`exchange-calendars==4.13.1`，仅改V5 outcomes既有工作流及测试/MOC；[同SHA main全库#44061816987](https://github.com/lican1213/a-share-momentum-runner/actions/runs/44061816987)329项+Wiki51页通过，业务[实际run #44061817000](https://github.com/lican1213/a-share-momentum-runner/actions/runs/44061817000)跑完test→真实OHLC→账本→归档；源码SHA`1825f6a829ae2bb5d7ac70b965044db0f6e3ef84`。
- [11/17 18:07四账户原始快照](../../records/national_team_paper_accounts_v5/2026-11-17/44061817000-a1.json)：前三组现金、历史平仓、决策及仓位与[17:18原快照](../../records/national_team_paper_accounts_v5/2026-11-17/44054114642-a1.json)逐项一致；新EARLY_ENTRY为`CASH_ONLY`、现金30000元、0持仓/0决策；`trade_authorized=false`、`broker_orders=[]`。已证明迁移和持续写入，不代表未来新事件可获利。
- 原11/16资金事件已在11/17 13:30冻结，参考原始SHA `a0c84975bfb0f1c64de9cea49029ecdd0d4ec3d7`，旧三组各2笔目标日11/18，11/17无开仓是正确时序。合并新策略不能将该旧冻结倒签为新增EARLY_ENTRY成交。下一独立新资金事件才检验早期组入场，后续按首次可得、同日期S0费后净收益和独立成熟簇做经济Gate。
