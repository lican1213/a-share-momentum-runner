"""No-network SSE direct response/unit + retry tests."""
import pytest
from national_team.sse_direct import parse_sse_payload,fetch_sse_direct

def payload(day="2026-10-27",amount="3623808.77"):
    return {"result":[{"SEC_CODE":"510300","STAT_DATE":day,"TOT_VOL":amount},
                      {"SEC_CODE":"510310","STAT_DATE":day,"TOT_VOL":"2192644.40"},
                      {"SEC_CODE":"510330","STAT_DATE":day,"TOT_VOL":"1350744.98"}]}

def test_SSE_wanfens_to_units_exactly_once():
    actual=parse_sse_payload(payload(),"2026-10-27")
    assert actual["510300"]=="36238087700.00"
    assert actual["510310"]=="21926444000.00"
    assert actual["510330"]=="13507449800.00"

def test_SSE_empty_or_wrong_date_is_not_same_as_zero_funds():
    assert parse_sse_payload(payload(),"2026-10-26")=={}
    with pytest.raises(ValueError,match="missing or invalid"):
        parse_sse_payload({},"2026-10-27")
    with pytest.raises(ValueError,match="invalid"):
        parse_sse_payload(payload(amount="NaN"),"2026-10-27")

def test_bounded_retry_and_attempt_timeout_is_passed():
    seen=[]
    def flaky(url,params,headers,timeout):
        seen.append(timeout)
        if len(seen)==1:raise ConnectionError("simulated")
        return payload()
    output=fetch_sse_direct("2026-10-27",getter=flaky,attempts=2,timeout=3)
    assert output["510300"]=="36238087700.00"
    assert seen==[3,3]

def test_no_unsafe_TLS_switch_in_direct_adapter():
    from pathlib import Path
    source=Path("national_team/sse_direct.py").read_text()
    assert "verify=False" not in source
