"""Generate a concise MOC view from actual national-team saved source records.

Never updates raw JSON or manually curated experiment / failure logs. A new
source attempt (possibly failed) is separated from the latest genuinely
completed four-ETF research factor and the latest usable watchlist.
"""
from __future__ import annotations
import json,os
from pathlib import Path
from datetime import datetime
from national_team.left_entry_v4 import digest

CATEGORIES={
    "national_team_etf":"ETF source attempts",
    "national_team_merged":"Four-fund merged funding",
    "national_team_watch":"CSI300 stock research watches",
    "national_team_pcf":"Official exchange PCF attempts",
    "national_team_events":"Frozen paper-event cohorts",
    "national_team_paper":"Matured paper outcomes",
    "national_team_audits":"Independent research integrity audit",
    "national_team_strategy":"Archived four-ETF V2 stock cohorts",
    "national_team_v3":"V3 dated market and four-ETF replay",
    "national_team_router":"V5 dated event router",
    "national_team_left_entry_v5":"V5 prospective frozen intents",
    "national_team_left_outcomes_v5":"V5 independent horizon path",
    "national_team_paper_accounts_v5":"V5 continuous paper ledger",
    "national_team_policy":"Official policy source observations",
}

def enumerate_records(root:Path)->list[tuple[str,Path,dict]]:
    found=[]
    for folder in CATEGORIES:
        for path in (root/"records"/folder).glob("*/*.json"):
            try:
                r=json.loads(path.read_text(encoding="utf-8"))
            except (ValueError,OSError):
                raise ValueError(f"unreadable source evidence JSON: {path}") from None
            if not isinstance(r,dict):
                raise ValueError(f"record is not a dict: {path}")
            found.append((folder,path,r))
    found.sort(key=lambda x:(x[1].parent.name,
                             int(x[1].stem.split("-")[0]) if x[1].stem.split("-")[0].isdigit() else 0,
                             x[1].name),reverse=True)
    return found

def last_for(records:list[tuple[str,Path,dict]],folder:str,predicate=None):
    for entry in records:
        if entry[0]==folder and (predicate is None or predicate(entry[2])):
            return entry
    return None

def relative_link(path:Path,reference_dir:Path)->str:
    return Path(os.path.relpath(path,reference_dir)).as_posix()

def recorded_status(record:dict)->str:
    # Missing status is not a failed source verification or a completed business gate.
    return str(record.get("status") or
               (record.get("funding_event") or {}).get("status") or "NO_STATUS_FIELD")

def generate(root:Path,*,now:str, records:list[tuple[str,Path,dict]]|None=None)->dict:
    if records is None:records=enumerate_records(root)
    wiki=root/"wiki"
    (wiki/"indices").mkdir(parents=True,exist_ok=True)
    (wiki/"compiled").mkdir(parents=True,exist_ok=True)
    index=wiki/"indices"/"national-team.md"
    briefing=wiki/"compiled"/"briefing.md"
    def marker(ident,kind,header):
        return f"---\nid: {ident}\ntype: {kind}\nstatus: maintained\nupdated: {now[:10]}\n---\n# {header}\n\n"
    lead=("Source-backed **captured observations**, not broker fills. "
          "Latest failed attempt does NOT invalidate prior historic source evidence; "
          "prior positive data is not a newly observed today's inflow. "
          "NO_STATUS_FIELD means the record has no summary status, not that an Actions run failed.\n\n"
          "[根MOC](../../MOC.md) · [E2E红队审计](../audits/AUD-2026-10-28-e2e-release-gate.md)\n\n")
    lines=["| Source class | Trade/record date | Run ID | Recorded status | Evidence |",
           "| --- | --- | --- | --- | --- |"]
    for folder,path,r in records:
        name=CATEGORIES[folder]
        date=str(r.get("funding_date") or r.get("asof_requested") or
                 r.get("asof") or path.parent.name)
        run=str(r.get("run_id") or path.stem)
        status=recorded_status(r)
        label=relative_link(path,index.parent)
        lines.append(f"| {name} | {date} | {run} | {status.replace('|','/')} | [JSON]({label}) |")
    if not records:lines.append("| No national-team source record | — | — | unavailable | — |")
    index.write_text(marker("GENERATED-NATIONAL-TEAM","log","国家队四ETF与股票追踪实际运行索引")
                     +lead+"\n".join(lines)+"\n",encoding="utf-8")
    attempt=last_for(records,"national_team_etf")
    full=last_for(records,"national_team_merged",
        lambda r:(r.get("funding_event") or {}).get("four_etf_factor") is not None)
    # The original successfully observed direct 4-fund factor may predate merge.
    if full is None:
        full=last_for(records,"national_team_etf",
            lambda r:(r.get("funding_event") or {}).get("four_etf_factor") is not None)
    watch=last_for(records,"national_team_watch",
                   lambda r:r.get("status")=="INDEX_PROXY_RESEARCH_WATCHLIST")
    frozen=last_for(records,"national_team_events")
    paper=last_for(records,"national_team_paper")
    pcf=last_for(records,"national_team_pcf")
    red=last_for(records,"national_team_audits")
    v2=last_for(records,"national_team_strategy",lambda r:r.get("model_version")=="NT_FLOW_PIT_V2_20261028" and r.get("status")=="FROZEN_PROSPECTIVE_RESEARCH" and r.get("new_event_count",0)>0)
    info=[
        "[根MOC](../../MOC.md) · [国家队所有实跑记录](../indices/national-team.md) · "
        "[模型演进](../models/registry.md) · [红队审计](../audits/AUD-2026-10-28-e2e-release-gate.md)",
        "",
        "**主线：中央汇金等法定主体披露（低频） × 固定四沪深300ETF资金份额（高频） → 指数/PCF对应股票 → S0 ETF基准 vs S1/S2选股组合。**",
        "",
    ]
    def bullet(label,entry):
        if entry is None:return f"- {label}：无可复核持久化记录。"
        folder,path,r=entry
        return (f"- {label}：[run {r.get('run_id',path.stem)}]({relative_link(path,briefing.parent)})；"
                f"状态 `{recorded_status(r)}`；"
                f"日期 {r.get('funding_date') or r.get('asof_requested') or r.get('asof') or path.parent.name}。")
    info.append(bullet("最新ETF源采集尝试",attempt))
    info.append(bullet("最近可完整核验四ETF份额/NAV的历史记录",full))
    if full is not None:
        _,path,r=full
        ev=r.get("funding_event") or {}
        fact=ev.get("four_etf_factor") or {}
        if fact:
            info.extend([
                f"- 最近完整基金资金研究日：**{fact.get('trade_date')}**；"
                f"合计当日净份额×NAV代理 **{fact.get('daily_net_creation_proxy_cny')} 元**；"
                "这不是汇金个人账户当日买入。",
                f"- 最近完整5日资金强度：**{(fact.get('five_day') or {}).get('net_creation_pct_initial_aum')}**；"
                "基金NAV尚需发行人原件复核、份额拆并需独立验证；极值应标异常而非直接买点。"
            ])
    info.append(bullet("最近真实指数权重代理股票观察名单",watch))
    if watch is not None:
        _,path,r=watch
        ranking=r.get("research_ranking") or {}
        info.append(f"- 最新实测股票样本数：**{ranking.get('ranked_from_n_stocks','未知')}**；"
                    f"指数权重覆盖约 **{r.get('pool_weight_coverage','未知')}**；"
                    "指数权重非ETF真实PCF，且未证明个股跟随收益。")
    v3 = last_for(records,"national_team_v3")
    router = last_for(records,"national_team_router")
    ledger = last_for(records,"national_team_paper_accounts_v5")
    outcomes = last_for(records,"national_team_left_outcomes_v5")
    intent = last_for(records,"national_team_left_entry_v5")
    info.extend(["", "**当前研究执行主线：V3资金 → V5路由 → 连续模拟盘；旧V2/A2/B仅历史归档。**",
                 bullet("V3最新回放",v3),bullet("V5最新事件路由",router),bullet("V5最近不可回写冻结",intent),
                 bullet("V5最新独立前瞻路径",outcomes),bullet("V5最新模拟账本",ledger)])
    if v3:
        _,_,r=v3
        quality=r.get("data_quality",{})
        latest=r.get("latest_session") or ((r.get("daily") or [{}])[-1])
        capture=(r.get("source_provenance") or {}).get("denominator_capture") or {}
        info.append(f"- 指数交易日 {quality.get('last_index_day')}；最新完整四份额日 {quality.get('last_full_four_share_day')}；"
                    f"普通覆盖率有效日 {quality.get('ratio_days')}，历史PIT核验日 {quality.get('ratio_pit_verified_days')}；"
                    f"最新分母采集 {capture.get('status','NOT_CAPTURED')}；当前ratio={latest.get('ordinary_float_coverage_ratio')}。")
    if router:
        _,_,r=router
        f=r.get("funding") or {};fb=r.get("feedback") or {}
        info.append(f"- 资金观察交易日 {r.get('signal_session')}；路由 {r.get('status')}；"
                    f"资金模式 {f.get('funding_basis','SHARE_PROXY_LEGACY')}；"
                    f"同额成熟10日独立簇 {fb.get('paired_10d_events')}/8；默认组 {r.get('selected_policy')}。")
        cohort = fb.get("exp0017_cohort") or {}
        early = (cohort.get("EARLY_ENTRY") or {}).get("10") or {}
        chase = (cohort.get("R_BOUNCE") or {}).get("10") or {}
        info.append(f"- EXP-0017 新规则10日成熟簇：早期 {early.get('matured_clusters', 0)}、"
                    f"追涨 {chase.get('matured_clusters', 0)}；"
                    "未成熟不能当作策略学习或真实成交。")
        complete = ((full[2].get("funding_event") or {}).get("four_etf_factor") or {}) if full else {}
        if f.get("exchange_shares_complete") is False or f.get("exchange_nav_complete") is False:
            info.append(f"- 资金证据降级：信号日 {r.get('signal_session')} 的交易所四ETF份额/NAV未齐；"
                        f"最近源端完整日 {complete.get('trade_date', '未知')}；"
                        "当前份额代理不是当日完整官方资金信号。")
    if ledger:
        _,_,r=ledger
        info.extend([f"- 账户市场日期 **{r.get('last_market_session')}**；捕获 {r.get('capture_time')}；纸面非券商成交。",
                 "", "| 组 | 现金 | 权益 | 持仓数 | 平仓数 | 扣费净盈亏 | 同额S0已实现超额 | mark_status |",
                 "| --- | --- | --- | --- | --- | --- | --- | --- |"])
        for arm,account in r.get("accounts",{}).items():
            summary=account.get("summary") or {}
            values=[arm,summary.get("cash_cny"),summary.get("equity_after_estimated_exit_cost_cny"),
                    summary.get("open_positions"),summary.get("closed_trades"),summary.get("net_pnl_cny"),
                    summary.get("realized_excess_s0_equal_capital_cny"),summary.get("mark_status")]
            info.append("| "+" | ".join(str(v) for v in values)+" |")
        decision_pairs = [(arm, d) for arm, account in r.get("accounts", {}).items()
                          for d in account.get("decisions", [])]
        decisions = [d for _, d in decision_pairs]
        ids = [d.get("id") for d in decisions]
        decision_conflict = (len(ids) != len(set(ids)) or
                             any(not key or len(key.split(":")) != 3 or
                                 key.split(":")[1] != arm
                                 for arm, d in decision_pairs for key in [d.get("id")]))
        if decision_conflict:
            info.append("- EVIDENCE_CONFLICT：账户决策ID重复、缺失或所属组不符；"
                        "累计入场与跳过数量不得当作已验证数据。")
        else:
            fills = sum(d.get("status") == "PAPER_OPEN_PROXY_FILLED" for d in decisions)
            skipped = sum(d.get("status") == "PAPER_ENTRY_SKIPPED" for d in decisions)
            info.append(f"- 累计账户决策：纸面开盘入场 {fills}、合法跳过 {skipped}；"
                        f"累计源事件 {r.get('source_event_count', '未知')}；"
                        "不把再次归档或 OHLC 开盘代理算新增实际交易。")
        if intent:
            _, _, frozen_intent = intent
            signal_day = frozen_intent.get("signal_session")
            next_session = (frozen_intent.get("measurement") or {}).get("next_session")
            planned = [f"{signal_day}:{arm}:{order['stock']}"
                       for arm, policy in (frozen_intent.get("paper_policies") or {}).items()
                       for order in (policy.get("orders") or []) if order.get("stock")]
            if decision_conflict or len(planned) != len(set(planned)):
                info.append("- EVIDENCE_CONFLICT：最新冻结意向重复或账户决策不唯一，"
                            "不得推断本批已成交、跳过或完成。")
            else:
                decisions_by_id = {d["id"]: d for d in decisions}
                filled = sum(decisions_by_id.get(key, {}).get("status") == "PAPER_OPEN_PROXY_FILLED"
                             for key in planned)
                skipped = sum(decisions_by_id.get(key, {}).get("status") == "PAPER_ENTRY_SKIPPED"
                              for key in planned)
                late = sum(decisions_by_id.get(key, {}).get("status") == "LATE_INTENT_NO_BACKFILL"
                           for key in planned)
                undecided = sum(key not in decisions_by_id for key in planned)
                other = len(planned) - filled - skipped - late - undecided
                info.append(f"- 最新冻结 {signal_day}：{len(planned)}条意向，"
                            f"已纸面入场 {filled}、按规则跳过 {skipped}、"
                            f"迟到不补单 {late}、无账户决策 {undecided}、其他状态 {other}；"
                            "按冻结日＋组别＋股票代码核对；独立OHLC情景不是账户成交。")
            last_session = r.get("last_market_session")
            if next_session and (not last_session or last_session < next_session):
                if now[:10] < next_session:
                    info.append(f"- 最新冻结拟于 {next_session} 开盘研究；"
                                f"账户市场日仍为 {last_session}，"
                                "预定市场日尚未到达，不得把意向当成入场。")
                elif now[:10] == next_session:
                    info.append(f"- 执行日待读回：预定 {next_session}，"
                                f"账户市场日仍为 {last_session}；"
                                "不能在收盘归档前宣称已执行。")
                else:
                    info.append(f"- OVERDUE_MARKET_READBACK：预定执行日 {next_session} 已过去，"
                                f"账本只到 {last_session}；检查真实源与Actions，禁止补写历史成交。")
            elif not decision_conflict and len(planned) == len(set(planned)) and undecided:
                info.append("- 生产缺口：账户市场日已达到预定执行日，但部分意向无账户决策；"
                            "须查实际行情及不可回写账本，不能倒签成交。")
    elif intent:
        info.append("- NO_PAPER_LEDGER：存在最新冻结但无连续模拟账户快照，"
                    "不得报告任何该批入场。")
    if outcomes:
        _, _, outcome = outcomes
        if ledger:
            _, _, paper_account = ledger
            arms = {"SHALLOW_DIP", "DEEP_DIP", "R_BOUNCE", "EARLY_ENTRY"}
            actual_accounts = paper_account.get("accounts") or {}
            summaries = outcome.get("paper_account_summary") or {}
            linked = (set(actual_accounts) == arms and set(summaries) == arms
                      and not decision_conflict
                      and paper_account.get("trade_authorized") is False
                      and outcome.get("trade_authorized") is False
                      and paper_account.get("broker_orders") == []
                      and outcome.get("broker_orders") == []
                      and bool(outcome.get("paper_account_snapshot_sha256"))
                      and outcome.get("paper_account_snapshot_sha256") == paper_account.get("snapshot_sha256")
                      and outcome.get("github_run_id") == paper_account.get("github_run_id")
                      and digest({k: v for k, v in paper_account.items() if k != "snapshot_sha256"})
                      == paper_account.get("snapshot_sha256")
                      and digest({k: v for k, v in outcome.items() if k != "snapshot_sha256"})
                      == outcome.get("snapshot_sha256")
                      and all(summaries[arm] == actual_accounts[arm].get("summary")
                              for arm in arms))
            info.append(f"- OHLC反馈与连续账本读回：{'MATCHED_SNAPSHOT' if linked else 'NOT_VERIFIED'}；"
                        f"反馈run {outcome.get('github_run_id')}、账户run {paper_account.get('github_run_id')}；"
                        "须四组完整、无决策ID冲突、非实盘授权、同run、原文哈希重算一致及四组汇总匹配。"
                        "此为文件完整性，不代表独立真实成交或策略盈利。")
        source_errors = sorted({code for result in (outcome.get("results") or [])
                                for policy in (result.get("policy_results") or {}).values()
                                for code in (policy.get("errors") or {})})
        if source_errors:
            info.append(f"- 本次OHLC跟踪来源异常（全批次）：{', '.join(source_errors)}；"
                        "需查原始错误及替代行情证据，不得当成精确盘口成交。")
        if router:
            router_time = router[2].get("observed_at")
            outcome_time = outcome.get("capture_time")
            source_sha = router[2].get("feedback_source_outcomes_snapshot_sha256")
            if (router_time and outcome_time and
                    datetime.fromisoformat(router_time) >= datetime.fromisoformat(outcome_time)
                    and source_sha and source_sha == outcome.get("snapshot_sha256")):
                info.append("- 后续路由反馈输入：MATCHED_SOURCE_SNAPSHOT；"
                            "路由明示消费的反馈哈希与最新结果一致，仍需核对策略选优与成熟样本。")
            elif router_time and outcome_time and datetime.fromisoformat(router_time) < datetime.fromisoformat(outcome_time):
                info.append(f"- 后续路由反馈读回仍待验收：路由run "
                            f"{router[2].get('github_run_id')}早于最新反馈run "
                            f"{outcome.get('github_run_id')}；新反馈尚未证明被路由消费。")
            else:
                info.append("- 后续路由反馈输入：UNVERIFIED_SOURCE_SNAPSHOT；"
                            "仅有较晚运行时间不能证明消费了最新OHLC反馈，"
                            "路由需留存所用反馈快照哈希才能关闭该Gate。")
    info.extend(["","**历史归档（不作为当前新信号）：**"])
    info.append(bullet("最近四ETF独立V2前瞻选股",v2))
    if v2 is not None:
        _,v2_path,v2_record=v2
        s1=[x["symbol"] for x in v2_record.get("s1_ranked",[])]
        s2=[x["symbol"] for x in v2_record.get("s2_ranked",[])]
        info.append(f"- V2真实首次可得时刻：{v2_record.get('strategy_first_public_at')}，底层四ETF资金日：{v2_record.get('flow_date')}；"
                    f"S1资金/成交额研究组 **{', '.join(s1)}**；"
                    f"S2独立价格确认研究组 **{', '.join(s2)}**。")
        info.append("- V2仅以资金为择时触发（CSI300代理权重跨ETF相同，不能辨识逐股票实际买盘）；"
                    "5/10/20日净超额收益待未来真实行情成熟；旧V1组合不可替换初始冻结股单。")
    for label,item in [
        ("最近PCF采集尝试",pcf),("最近纸面事件冻结",frozen),
        ("最近纸面收益观察",paper),("最近独立实跑红队审计",red)]:
        info.append(bullet(label,item))
    info.extend(["", "**投资结果状态：暂无独立样本外净超额收益验证；不推断任何国家队真实账户买卖、已成交订单或必然盈利。**",
                "", "自动页面仅汇总已保存的证据。最新综合workflow是否为绿色，仍需单独查GitHub Actions对应SHA。"])
    briefing.write_text(marker("COMPILED-BRIEFING","overview","国家队资金→成分股研究 Agent 最新证据简报")
                        +"\n".join(info)+"\n",encoding="utf-8")
    return {"national_team_records":len(records),"sources_index":str(index),
            "briefing":str(briefing),"last_complete_four_run":full[2].get("run_id") if full else None}
