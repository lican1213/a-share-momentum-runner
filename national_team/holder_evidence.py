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

def main():
    file=Path("data/national_team_holders/159919-2024H1-2025H1.json")
    result=verify_ledger(json.loads(file.read_text(encoding="utf-8")))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
