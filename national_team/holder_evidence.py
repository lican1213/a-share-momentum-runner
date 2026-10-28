"""Legal-holder evidence is separate from whole-ETF flow proxies.

Period-end company holdings are only knowable after original report publication.
Changing fund total shares cannot be attributed to any legal entity.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
import json

LEGAL_ENTITIES={
 "中央汇金投资有限责任公司":"HUijin_Investment",
 "中央汇金资产管理有限责任公司":"Huijin_Asset_Management",
}
class HolderEvidenceError(ValueError):pass

def verify_ledger(data:dict)->dict:
    if data.get("asset") not in ("159919","510300","510310","510330"):
        raise HolderEvidenceError("not a fixed original ETF")
    if data.get("units")!="fund_shares":
        raise HolderEvidenceError("wrong fund share unit")
    periods={}
    for source in data.get("sources",[]):
        period=source["period_end"]
        announced=source["first_public_date"]
        try:
            pe,an=date.fromisoformat(period),date.fromisoformat(announced)
        except ValueError:raise HolderEvidenceError("bad report or publication date")
        if an<=pe:raise HolderEvidenceError("report not published after period end")
        if source.get("source_type")!="FUND_MANAGER_HALF_YEAR_REPORT" or not str(source.get("url","")).startswith("https://"):
            raise HolderEvidenceError("missing official fund source metadata")
        if not isinstance(source.get("pdf_page"),int) or source["pdf_page"]<1:
            raise HolderEvidenceError("cannot locate holder page in original PDF")
        if period in periods:raise HolderEvidenceError("duplicated report period")
        periods[period]=source
    obs={}
    for row in data.get("observations",[]):
        period=row["period_end"];entity=row["entity"]
        if period not in periods:raise HolderEvidenceError("no linked original report")
        if entity not in LEGAL_ENTITIES:raise HolderEvidenceError("unknown entity; do not fold funds into Huijin")
        try:
            n=Decimal(str(row["shares"]))
        except (ValueError,InvalidOperation):raise HolderEvidenceError("invalid shares")
        if not n.is_finite() or n<0 or n!=n.to_integral_value():
            raise HolderEvidenceError("negative, fractional or NaN fund shares")
        key=(period,entity)
        if key in obs:raise HolderEvidenceError("duplicate legal holder")
        obs[key]=n
    if not obs:raise HolderEvidenceError("no confirmed observations")
    report_periods=sorted(periods)
    comparisons=[]
    for before,after in zip(report_periods[:-1],report_periods[1:]):
        for entity in LEGAL_ENTITIES:
            if (before,entity) not in obs or (after,entity) not in obs:
                continue
            change=obs[(after,entity)]-obs[(before,entity)]
            comparisons.append({
              "fund_code":data["asset"],"entity":entity,
              "from_period_end":before,"to_period_end":after,
              "source_first_public_date":periods[after]["first_public_date"],
              "previous_shares":format(obs[(before,entity)],"f"),
              "current_shares":format(obs[(after,entity)],"f"),
              "change_in_reported_shares":format(change,"f"),
              "direction":"INCREASE" if change>0 else "DECREASE" if change<0 else "UNCHANGED",
              "not_trade_date_or_fill_price":True,
              "evidence":"LEGAL_HOLDER_PERIOD_END_REPORT"}
            )
    return {"fund_code":data["asset"],"holder_records":len(obs),
            "periods":report_periods,"comparisons":comparisons,
            "latest_period_end":max(periods),
            "latest_report_public_at":periods[max(periods)]["first_public_date"],
            "do_not_attribute_ETF_daily_shares_to_specific_investor":True}

def evidence_as_known_at(data:dict,public_date:str)->dict:
    # A 2025-06-30 holder snapshot may be unavailable before Aug 29.
    cutoff=date.fromisoformat(public_date)
    src={p:s for p,s in ((x["period_end"],x) for x in data["sources"])
         if date.fromisoformat(s["first_public_date"])<=cutoff}
    if not src:return {"status":"NO_PUBLISHED_HOLDER_EVIDENCE","cutoff":public_date}
    subset={**data,"sources":list(src.values()),
            "observations":[x for x in data["observations"] if x["period_end"] in src]}
    report=verify_ledger(subset)
    return {"status":"PUBLISHED_PERIOD_END_HOLDINGS","cutoff":public_date,**report}

def reconcile_latest_total_historical_holders(history:dict,latest:dict,
                                              asof_public_date:str)->dict:
    """Anomaly screen: 2025 disclosed named holdings cannot exceed the entire
    ETF outstanding share total from an already-public 2026 report.
    This is NOT evidence assigning redemption trades to named accounts.
    """
    cutoff=date.fromisoformat(asof_public_date)
    observed=evidence_as_known_at(history,asof_public_date)
    if observed["status"]!="PUBLISHED_PERIOD_END_HOLDINGS":
        return {"status":"HISTORICAL_HOLDER_NOT_YET_PUBLISHED"}
    if history["asset"]!=latest.get("asset") or latest.get("unit")!="fund_shares":
        raise HolderEvidenceError("fund mismatch or unit mismatch")
    pe=date.fromisoformat(str(latest["period_end"]))
    release=date.fromisoformat(str(latest["first_public_date"]))
    if release<=pe:
        raise HolderEvidenceError("fund-total report must be released after period close")
    if release>cutoff:
        return {"status":"LATER_FUND_TOTAL_NOT_YET_PUBLIC","asof":asof_public_date}
    if not str(latest.get("source_url","")).startswith("https://") or not latest.get("source_section"):
        raise HolderEvidenceError("aggregate fund shares lack traceable report source")
    try:
        total=Decimal(str(latest["total_fund_shares"]))
        institution=Decimal(str(latest["institutional_shares"]))
        individual=Decimal(str(latest["individual_shares"]))
    except (ValueError,TypeError,InvalidOperation):
        raise HolderEvidenceError("invalid latest fund total") from None
    if min(total,institution,individual)<0 or not all(x.is_finite() for x in (total,institution,individual)):
        raise HolderEvidenceError("negative/nonfinite fund shares")
    if total!=institution+individual or total<=0:
        raise HolderEvidenceError("fund aggregate does not reconcile")
    prior_period=max(x["period_end"] for x in history["sources"]
                     if date.fromisoformat(x["first_public_date"])<=cutoff
                     and x["period_end"]<latest["period_end"])
    held=sum((Decimal(str(x["shares"])) for x in history["observations"]
              if x["period_end"]==prior_period and x["entity"] in LEGAL_ENTITIES),Decimal(0))
    excess=max(held-total,Decimal(0))
    return {
        "status":"HISTORICAL_NATIONAL_TEAM_HOLDINGS_EXCEED_NEW_TOTAL"
                if held>total else "LATEST_TOTAL_NOT_BELOW_PRIOR_NAMED_HOLDINGS",
        "legal_holder_snapshot_asof":prior_period,
        "new_fund_total_period":latest["period_end"],
        "new_fund_total_first_public_date":latest["first_public_date"],
        "historical_two_Huijin_entities_shares":format(held,"f"),
        "new_whole_fund_total_shares":format(total,"f"),
        "prior_combined_holdings_exceed_new_total_by_shares":format(excess,"f"),
        "new_total_is_identity_specific":False,
        "can_assert_prior_named_holdings_unchanged_in_new_period":held<=total,
        "proved_exact_sale_dates_or_counterparties":False,
        "corporate_action_comparability_requires_verification":True,
        "fund_report_source":latest["source_url"],
        "interpretation":"Past named positions cannot both remain unchanged at latest fund total; no identified investor-level trades are inferred."
    }


def main():
    file=Path("data/national_team_holders/159919-2024H1-2025H1.json")
    result=verify_ledger(json.loads(file.read_text(encoding="utf-8")))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
