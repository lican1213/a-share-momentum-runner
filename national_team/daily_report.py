"""Decision-facing, auditable national-team research digest from persisted facts.

Never promote a historical Huijin holding or whole-ETF flow to investor's
specific intraday purchases. Runs AFTER evidence archival, not during data
retrieval. Immutable per-source-run report plus replaceable Wiki summary.
"""
from __future__ import annotations
import json
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from zoneinfo import ZoneInfo
from national_team.holder_evidence import evidence_as_known_at

ROOT=Path(__file__).resolve().parents[1]

def _valid_rank(watch,merged):
    ranking=watch.get("research_ranking") or {}
    last=(merged.get("funding_event") or {}).get("latest_available_trading_day")
    return (watch.get("status")=="INDEX_PROXY_RESEARCH_WATCHLIST"
            and ranking.get("not_actual_ETF_PCF") is True
            and watch.get("funding_date")==last
            and bool(watch.get("event_first_public_no_earlier_than")))

def compile_digest(merged,watch,events,paper,audit,holder):
    fund=merged.get("funding_event") or {}
    assessment=audit.get("status","MISSING")
    pass_audit=assessment in ("RESEARCH_PRIOR_FOUR_CURRENT_PARTIAL_AUDITED",
                               "RESEARCH_DATA_AUDIT_PASS",
                               "RESEARCH_PARTIAL_SOURCES_AUDITED")
    if audit.get("failures"):
        pass_audit=False
    candidate_ok=pass_audit and _valid_rank(watch,merged)
    factor=fund.get("four_etf_factor") or {}
    partial=fund.get("partial_funding") or {}
    full_date=factor.get("trade_date")
    partial_dates=partial.get("period") or []
    if full_date and full_date!=fund.get("latest_complete_four_etf_factor_date"):
        raise ValueError("verified full factor date does not match explicit source date")
    if candidate_ok and watch["research_ranking"].get("data_scope")=="FOUR_ETF_DATED_SHARE_FLOW":
        if watch["funding_date"]!=full_date:
            raise ValueError("watch claims full four funds for different trading day")
    direct=evidence_as_known_at(holder, merged.get("first_observed_no_earlier_than", "")[:10])
    ranked=(watch.get("research_ranking") or {}) if candidate_ok else {}
    frozen=events.get("events") or []
    if candidate_ok and frozen:
        symbol_sets={x["strategy_id"]:x["candidate_symbols"] for x in frozen}
        pool=ranked.get("candidates",[])
        if "S1_FLOW_OVER_ADV20" in symbol_sets:
            expected=[x["symbol"] for x in pool[:5]]
            if symbol_sets["S1_FLOW_OVER_ADV20"]!=expected:
                raise ValueError("frozen S1 list is not identical to source watch order")
    latest_paper=[]
    for r in paper.get("result_records",[])[:20]:
        ev=r.get("evaluation") or {}
        horizons=ev.get("results") or {}
        latest_paper.append({"event_id":r.get("id"),
            "status":r.get("status") or ev.get("status") or "UNKNOWN",
            "horizon_statuses":{h:v.get("status") for h,v in horizons.items()}})
    return {
       "schema":1,"status":"EVIDENCE_BACKED_RESEARCH_DIGEST" if candidate_ok else "PARTIAL_RESEARCH_DIGEST",
       "original_four_funds":["510300","510310","510330","159919"],
       "asof_requested":merged.get("asof_requested"),
       "latest_full_four_funding_date":full_date,
       "full_four_daily_flow_cny":factor.get("daily_net_creation_proxy_cny"),
       "full_four_five_day_intensity":(factor.get("five_day") or {}).get("net_creation_pct_initial_aum"),
       "latest_partial_funding_dates":partial_dates,
       "latest_partial_fund_scope":partial.get("funds",[]),
       "latest_partial_flow_cny":partial.get("net_creation_proxy_cny"),
       "latest_ranked_stock_date":watch.get("funding_date") if candidate_ok else None,
       "ranked_stocks_count":ranked.get("ranked_from_n_stocks",0),
       "index_weight_coverage":watch.get("pool_weight_coverage") if candidate_ok else None,
       "fund_flow_scope":ranked.get("data_scope"),
       "S1_observation":ranked.get("candidates",[])[:5],
       "S2_frozen_observation":next((e.get("candidate_symbols",[]) for e in frozen
                          if e.get("strategy_id")=="S2_FLOW_PLUS_PRICE_STRENGTH"),[]),
       "paper_results":latest_paper,
       "last_known_legal_holder":direct,
       "legal_holder_data_is_current_day_trading_activity":False,
       "fund_flow_identifies_a_specific_national_team_investor":False,
       "stock_weight_source":"CSI300_LATEST_INDEX_WEIGHT_PROXY_NOT_ETF_PCF" if candidate_ok else None,
       "independent_after_cost_alpha_validated":False,
       "audit_status":assessment,
       "audit_approved_candidate_display":candidate_ok,
       "warning":"CSI300 index weights are NOT real ETF PCF execution; event stocks are for prospective observation",
    }

def human_readable(d)->str:
    def amt(v):
        return "尚无完整数据" if v is None else f"{Decimal(str(v))/Decimal(100000000):+.2f}亿元"
    def pct(v):
        return "尚无" if v is None else f"{Decimal(str(v))*100:+.2f}%"
    lines=["# 国家队相关ETF资金与个股观察简报","",
      f"- 数据截止：{d['asof_requested']}（研究账本；不等于实时国家队订单）",
      f"- 独立审计：{d['audit_status']}","",
      "## 核心四只ETF资金",
      f"- 最近完整四ETF日：{d['latest_full_four_funding_date'] or '尚无'}，当日净申赎代理 {amt(d['full_four_daily_flow_cny'])}；五交易日资金强度 {pct(d['full_four_five_day_intensity'])}",
      f"- 最新部分资金日期：{' → '.join(d['latest_partial_funding_dates']) if d['latest_partial_funding_dates'] else '无'}，覆盖{','.join(d['latest_partial_fund_scope']) or '无'}，合计 {amt(d['latest_partial_flow_cny'])}",
      "- 四ETF日期与最新部分资金日期可能不同，不可相加或写成同一个交易日。",
      f"- 完整四ETF是否来自先前独立重算的归档：{'是，参见来源路径 '+d.get('full_four_prior_source_path','') if d.get('full_four_factor_carried_forward') else '否或无足额资料'}","",
      "## S1 资金敞口／成交额研究观察",
      f"- 股票研究日期：{d['latest_ranked_stock_date'] or '无'}；实际覆盖 {d['ranked_stocks_count']}只；指数权重池占比 {pct(d['index_weight_coverage'])}",
    ]
    if d["S1_observation"]:
        for rank,x in enumerate(d["S1_observation"],1):
            ratio=Decimal(str(x["signed_exposure_over_adv20"]))*100
            lines.append(f"{rank}. {x['symbol']}：潜在指数敞口/ADV20 {ratio:.2f}%（并非真实买盘）")
    else: lines.append("- 没有通过当前研究证据的观察名单。")
    fund_alert=d.get("latest_fund_total_holder_consistency") or {}
    if fund_alert.get("status")=="HISTORICAL_NATIONAL_TEAM_HOLDINGS_EXCEED_NEW_TOTAL":
        lines.extend(["", "## 重要身份冲突：不得沿用旧汇金仓位",
          f"- 2025年中报所列汇金两主体合计：{Decimal(fund_alert['historical_two_Huijin_entities_shares'])/Decimal(100000000):.2f}亿份；2026年6月底**整只基金**总份额：{Decimal(fund_alert['new_whole_fund_total_shares'])/Decimal(100000000):.2f}亿份。",
          f"- 旧持仓合计超过后期整个基金总份额至少 {Decimal(fund_alert['prior_combined_holdings_exceed_new_total_by_shares'])/Decimal(100000000):.2f}亿份。不能把2025年汇金持仓写成2026年仍然持有，也不能用基金总份额反推出各法人具体减持日期。",
          "- 需要核对2026年基金持有人明细与任何ETF份额折算；这是一条身份有效性**红队异常**，不是推定某主体当天实际卖单。"])
    lines+=["","## S2 与验证状态",
      "- 冻结S2："+(", ".join(d["S2_frozen_observation"]) if d["S2_frozen_observation"] else "无新增冻结事件"),
      "- 现有纸面观察："+(", ".join(f"{x['event_id']}:{x['status']}" for x in d["paper_results"]) if d["paper_results"] else "未找到成熟结果"),
      "- 5/10/20交易日扣成本、样本外能否跑赢直接买沪深300ETF：**尚未证实**。","",
      "## 国家队法定身份与误归因防线",
      f"- 159919已核实持仓最新报告期：{d['last_known_legal_holder'].get('latest_period_end','未录入')}，报告公开日期：{d['last_known_legal_holder'].get('latest_report_public_at','未知')}",
      "- 存量持仓只证明报告期末持有情况；整只ETF净申购不能认定为中央汇金当日买入。",
      "- S1/S2基于中证300指数权重代理，尚未拿到充分核验的逐日实际ETF PCF及其现金替代数据。"]
    return "\n".join(lines)+"\n"

def latest_artifact(folder:Path):
    items=sorted(folder.glob("*/*.json"),key=lambda p:p.stat().st_mtime,reverse=True)
    if not items:raise FileNotFoundError(f"no evidence in {folder}")
    return items[0]

def supplement_prior_full_four(digest:dict,root:Path,*,signal_public_at:str)->dict:
    """Carry forward a separately archived/independently audited 4-ETF day.

    Prior record must have been captured by the time the stock watch was frozen,
    and never be dated after the currently displayed partial-flow date. Do not
    infer an investor-specific buy from a historical complete four-ETF factor.
    """
    if digest.get("latest_full_four_funding_date"):
        digest["full_four_factor_carried_forward"]=False
        return digest
    from national_team.audit_gate import check_funding
    from national_team.core_flow_factors import utc_aware
    end=utc_aware(signal_public_at,"watch disclosure cut-off")
    max_fund_day=digest.get("latest_ranked_stock_date") or digest.get("asof_requested")
    possible=[]
    for p in (root/"records/national_team_merged").glob("*/*.json"):
        try:
            obj=json.loads(p.read_text(encoding="utf-8"))
            earliest=utc_aware(obj.get("first_observed_no_earlier_than"),
                               "prior archived disclosure")
            factor=(obj.get("funding_event") or {}).get("four_etf_factor") or {}
            date_value=factor.get("trade_date")
            if earliest>end or not date_value or date_value>max_fund_day:
                continue
            verified=check_funding(obj)
            if verified.get("verified") is not True:
                continue
            possible.append((date_value,earliest,p,factor))
        except (OSError,ValueError,KeyError,AssertionError):
            continue
    if not possible:
        digest["full_four_factor_carried_forward"]=False
        return digest
    date_value,first,p,factor=max(possible,key=lambda r:(r[0],r[1]))
    digest["latest_full_four_funding_date"]=date_value
    digest["full_four_daily_flow_cny"]=factor["daily_net_creation_proxy_cny"]
    digest["full_four_five_day_intensity"]=factor["five_day"]["net_creation_pct_initial_aum"]
    digest["full_four_factor_carried_forward"]=True
    digest["full_four_prior_source_path"]=str(p.relative_to(root))
    digest["full_four_prior_first_observed_at"]=first.isoformat()
    return digest


def recover_original_frozen_s2(digest:dict,root:Path,*,public_at:str)->dict:
    """Restore an already-frozen S2 list when a later run marks it duplicate.

    Do NOT create a new signal from the latest rank or replace the first
    prospective cohort. A newer run must never backdate or overwrite the first.
    """
    if digest.get("S2_frozen_observation"):
        digest["S2_restored_from_earlier_immutable_event"]=False
        return digest
    from national_team.core_flow_factors import utc_aware
    current=utc_aware(public_at,"current watch capture")
    day=digest.get("latest_ranked_stock_date")
    possible=[]
    for p in (root/"records/national_team_events").glob("*/*.json"):
        try:
            obj=json.loads(p.read_text(encoding="utf-8"))
            for ev in obj.get("events",[]):
                if ev.get("strategy_id")!="S2_FLOW_PLUS_PRICE_STRENGTH":
                    continue
                if ev.get("funding_underlying_day")!=day:
                    continue
                when=utc_aware(ev.get("first_public_at"),"S2 first publication")
                if when>current:continue
                if not ev.get("candidate_symbols"):continue
                possible.append((when,p,ev))
        except (OSError,ValueError,KeyError):
            continue
    if not possible:return digest
    when,p,event=min(possible,key=lambda z:z[0])
    digest["S2_frozen_observation"]=list(event["candidate_symbols"])
    digest["S2_restored_from_earlier_immutable_event"]=True
    digest["S2_immutable_event_id"]=event["id"]
    digest["S2_immutable_event_source"]=str(p.relative_to(root))
    digest["S2_original_frozen_at"]=when.isoformat()
    return digest


def compile_latest(root:Path=ROOT):
    # Choose latest watch for which all same-run companions exist.
    for watch_path in sorted((root/"records/national_team_watch").glob("*/*.json"),
                             key=lambda p:(p.parent.name,p.stem),reverse=True):
        stem=watch_path.name;day=watch_path.parent.name
        required={
          "merged":root/"records/national_team_merged"/day/stem,
          "events":root/"records/national_team_events"/day/stem,
          "paper":root/"records/national_team_paper"/day/stem,
          "audit":root/"records/national_team_audits"/day/stem,
        }
        if all(p.is_file() for p in required.values()):
            read=lambda p:json.loads(p.read_text(encoding="utf-8"))
            inputs={key:read(p) for key,p in required.items()}
            holder=read(root/"data/national_team_holders/159919-2024H1-2025H1.json")
            watch=read(watch_path)
            result=compile_digest(inputs["merged"],watch,inputs["events"],inputs["paper"],inputs["audit"],holder)
            public_at=watch.get("event_first_public_no_earlier_than") or inputs["merged"]["first_observed_no_earlier_than"]
            result=supplement_prior_full_four(result,root,signal_public_at=public_at)
            result=recover_original_frozen_s2(result,root,public_at=public_at)
            from national_team.holder_evidence import reconcile_latest_total_historical_holders
            total_path=root/"data/national_team_holders/159919-2026H1-fund-total.json"
            if total_path.is_file():
                total=read(total_path)
                result["latest_fund_total_holder_consistency"]=reconcile_latest_total_historical_holders(
                    holder,total,public_at[:10])
                result["latest_fund_total_original_source"]=total.get("source_url")
            result["source_paths"]={k:str(p.relative_to(root)) for k,p in required.items()}
            result["source_paths"]["watch"]=str(watch_path.relative_to(root))
            return day,stem,result
    raise FileNotFoundError("no complete set of real source, watch, frozen and red-team records")

def main():
    day,stem,data=compile_latest()
    folder=ROOT/"records/national_team_daily"/day
    folder.mkdir(parents=True,exist_ok=True)
    # v2 is a new immutable interpretation, not an overwrite of the older
    # v1 snapshot: both research reports remain inspectable by future agents.
    jsonfile=folder/stem.replace(".json","-v4.json")
    mdfile=folder/stem.replace(".json","-v4.md")
    if not jsonfile.exists():
        jsonfile.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if not mdfile.exists():
        mdfile.write_text(human_readable(data),encoding="utf-8")
    summary=ROOT/"wiki/compiled/national_team_daily.md"
    summary.parent.mkdir(parents=True,exist_ok=True)
    wiki_frontmatter=(f"---\\nid: NT-COMPILED-DAILY\\ntype: compiled\\n"
                      f"status: active\\nupdated: {day}\\n---\\n").replace("\\n","\n")
    summary.write_text(wiki_frontmatter+human_readable(data),encoding="utf-8")
    print(json.dumps({"status":data["status"],"evidence":str(jsonfile.relative_to(ROOT)),
                      "watch_count":data["ranked_stocks_count"]},ensure_ascii=False))
if __name__=="__main__":main()
