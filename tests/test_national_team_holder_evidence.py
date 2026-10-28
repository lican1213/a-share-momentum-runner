"""Original public reports, independently traceable legal-entity holdings (not trades)."""
import copy,json
from pathlib import Path
import pytest
from national_team.holder_evidence import HolderEvidenceError,verify_ledger,evidence_as_known_at

def original():
    return json.loads(Path("data/national_team_holders/159919-2024H1-2025H1.json").read_text(encoding="utf-8"))

def test_exact_huijin_two_legal_entities_and_genuine_period_comparison():
    obj=verify_ledger(original())
    assert obj["holder_records"]==4
    invest,asset={r["entity"]:r for r in obj["comparisons"]}.values() if False else (None,None)
    rows={r["entity"]:r for r in obj["comparisons"]}
    assert rows["中央汇金投资有限责任公司"]["change_in_reported_shares"]=="0"
    assert rows["中央汇金资产管理有限责任公司"]["change_in_reported_shares"]=="15141224273"
    assert rows["中央汇金资产管理有限责任公司"]["source_first_public_date"]=="2025-08-29"
    assert rows["中央汇金资产管理有限责任公司"]["not_trade_date_or_fill_price"]

def test_dont_know_2025_period_end_holdings_until_late_august_disclosure():
    r=evidence_as_known_at(original(),"2025-07-01")
    assert r["status"]=="PUBLISHED_PERIOD_END_HOLDINGS"
    assert r["latest_period_end"]=="2024-06-30"
    assert r["comparisons"]==[]
    later=evidence_as_known_at(original(),"2025-08-30")
    assert later["latest_period_end"]=="2025-06-30"
    assert len(later["comparisons"])==2

def test_no_false_identity_equivalence_or_missing_original_report():
    data=original()
    data["observations"][0]["entity"]="中国证券金融股份有限公司"
    with pytest.raises(HolderEvidenceError,match="unknown entity"):
        verify_ledger(data)
    data=original()
    data["sources"][0]["url"]="https://"
    # URL is not suitable to trace a specific original report.
    data["sources"][0]["url"]="missing report"
    with pytest.raises(HolderEvidenceError,match="official fund"):
        verify_ledger(data)

def test_reject_bad_report_dates_and_malformed_fund_shares():
    data=original()
    data["sources"][0]["first_public_date"]="2024-01-01"
    with pytest.raises(HolderEvidenceError,match="not published"):
        verify_ledger(data)
    data=original()
    data["observations"][2]["shares"]="-1"
    with pytest.raises(HolderEvidenceError,match="negative"):
        verify_ledger(data)
