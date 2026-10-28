"""Red-team regression tests for dated SZSE 159919 JSON fallback.

All fixtures are explicitly synthetic; the live job separately probes the API.
"""
import pytest
from national_team.szse_json import parse_szse_page, fetch_one_szse_fund

def payload(rows,pagecount=1):
    return [{"metadata":{"pagecount":pagecount},"data":rows}]

def test_ten_thousand_shares_converted_exactly_once():
    data=payload([{"fund_code":"159919","size_date":"2026-10-27",
                   "current_size":"1,039,611.6676"}])
    parsed,pages=parse_szse_page(data,"159919","2026-10-20","2026-10-28")
    assert parsed=={"2026-10-27":"10396116676.0000"}
    assert pages==1

def test_pagination_over_two_pages_and_date_scope():
    invoked=[]
    def getter(url,*,params,headers,timeout):
        invoked.append(params["tab1PAGENO"])
        p=int(params["tab1PAGENO"])
        return payload([{"fund_code":"159919","size_date":f"2026-10-{20+p}",
                         "current_size":str(200+p)}],pagecount=2)
    d=fetch_one_szse_fund("159919","2026-10-01","2026-10-28",getter=getter)
    assert invoked==["1","2"]
    assert d=={"2026-10-21":"2010000","2026-10-22":"2020000"}

def test_not_silently_accept_missing_schema():
    with pytest.raises(ValueError,match="JSON array"):
        parse_szse_page({}, "159919","2026-10-01","2026-10-28")
    with pytest.raises(ValueError,match="invalid share"):
        parse_szse_page(payload([{"fund_code":"159919","size_date":"2026-10-27",
                       "current_size":"bad"}]),"159919","2026-10-01","2026-10-28")
    with pytest.raises(ValueError,match="outside request"):
        parse_szse_page(payload([{"fund_code":"159919","size_date":"2026-11-02",
                       "current_size":"1"}]),"159919","2026-10-01","2026-10-28")

def test_no_implicit_tls_disable_in_live_adapter():
    from pathlib import Path
    s=Path("national_team/szse_json.py").read_text()
    assert "verify=False" not in s
    assert "current_size" in s
