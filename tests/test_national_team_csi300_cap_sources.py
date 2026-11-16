"""Adversarial fixtures for exact date/unit/provenance; no network."""
from datetime import datetime
import json
import pytest
from national_team.csi300_cap_sources import BJ, KIND, parse_quote, final_index_sessions, add_captures

def fixture():
    close_at = datetime(2026,11,13,15,0,tzinfo=BJ)
    now = datetime(2026,11,13,18,0,tzinfo=BJ)
    payload = {"data":{"f57":"000300","f58":"沪深300","f43":4016.29,
                       "f116":50_840_000_000_000,"f117":48_180_000_000_000,
                       "f124":int(close_at.timestamp())}}
    return payload, {"2026-11-13":4016.29}, now

def test_exact_quote_date_unit_and_provenance():
    payload, prices, now = fixture()
    row = parse_quote(payload, prices, now)
    assert row["kind"] == KIND and row["unit"] == "CNY"
    assert row["value_cny"] == 48_180_000_000_000
    assert row["published_at"] == now.isoformat()
    assert "NOT_ORIGINAL_PUBLICATION" in row["method"]

@pytest.mark.parametrize("field,value",[("f57","000001"),("f43",4017),("f117",0),
                                        ("f117",60_000_000_000_000),("f124",0)])
def test_reject_wrong_or_unverifiable_source(field,value):
    payload,prices,now=fixture()
    payload["data"][field]=value
    with pytest.raises(ValueError):
        parse_quote(payload,prices,now)

def test_never_use_partial_intraday_index():
    _,prices,now=fixture()
    assert final_index_sessions(prices,now.replace(hour=12)) == {}
    assert final_index_sessions(prices,now) == prices

def test_append_prior_vendor_evidence_without_silent_conflict(tmp_path):
    payload,prices,now=fixture()
    row=parse_quote(payload,prices,now)
    capture={"status":"VENDOR_DATED_ORDINARY_FLOAT","record":row}
    folder=tmp_path/"2026-11-13"; folder.mkdir()
    (folder/"prior.json").write_text(json.dumps({"source_provenance":{"denominator_capture":capture}}))
    caps,report=add_captures({},tmp_path,{"status":"SOURCE_UNAVAILABLE"})
    assert caps[("2026-11-13",KIND)]["value_cny"]==row["value_cny"]
    revised={"status":"VENDOR_DATED_ORDINARY_FLOAT","record":{**row,"value_cny":row["value_cny"]+100}}
    caps,report=add_captures({},tmp_path,revised)
    assert not caps and report["conflicted_dates"]==["2026-11-13"]
