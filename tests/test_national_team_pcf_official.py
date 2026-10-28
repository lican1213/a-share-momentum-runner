"""PCF data contract regressions; fixture generated locally without network."""
from datetime import datetime
import pytest
from national_team.pcf_official import parse_official_html

CAP="2026-10-28T22:00:00+08:00"
def fixture(code="510300",day="2026-10-27",count=110):
    rows="".join(f"<tr><td>{600000+i}</td><td>Stock</td><td>{100+i}</td><td>允许</td></tr>"
                 for i in range(count))
    return (f"<html><body><div>最新公告日期 {day}</div><div>基金代码 {code}</div>"
            f"<table><tr><th>证券代码</th><th>证券简称</th><th>股票数量(股)</th>"
            f"<th>现金替代标志</th></tr>{rows}</table></body></html>")

def test_parsed_official_PCF_records_component_quantities_and_cash_substitute():
    result=parse_official_html(fixture(),"510300",CAP)
    assert result["status"]=="OFFICIAL_DATED_PCF_COMPONENTS_CAPTURED"
    assert result["pcf_date"]=="2026-10-27"
    assert result["component_count"]==110
    assert result["components"][0]["basket_shares_per_creation_unit"]==100
    assert result["components"][0]["cash_substitution"]=="允许"
    assert result["component_stock_values_and_PCF_weights_not_yet_verified"]

def test_date_missing_is_not_invented():
    html=fixture().replace("最新公告日期 2026-10-27","")
    r=parse_official_html(html,"510300",CAP)
    assert r["status"]=="NO_DATED_OFFICIAL_PCF_IN_HTTP_RESPONSE"

def test_wrong_fund_and_future_pcf_rejected():
    with pytest.raises(ValueError,match="identity"):
        parse_official_html(fixture(code="510330"),"510300",CAP)
    with pytest.raises(ValueError,match="after capture"):
        parse_official_html(fixture(day="2026-10-29"),"510300",CAP)

def test_tiny_partial_table_cannot_pass_as_full_pcf():
    r=parse_official_html(fixture(count=8),"510300",CAP)
    assert r["status"]=="DATED_PCF_BUT_CONSTITUENTS_NOT_IN_STATIC_RESPONSE"
    assert r["parsed_components"]==8
