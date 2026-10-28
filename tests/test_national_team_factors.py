"""Pure arithmetic regression tests only. These fixtures are NOT real ETF data."""
import copy
from decimal import Decimal
import pytest

from national_team.core_flow_factors import (
    calculate, CORE_FOUR, EXPANDED_ONLY, DataGateError,
)

DAYS = ["2026-10-19", "2026-10-20", "2026-10-21",
        "2026-10-22", "2026-10-23", "2026-10-26"]
CUTOFF = "2026-10-27T08:30:00+08:00"


def sample_panel():
    panel = {}
    for n, day in enumerate(DAYS):
        panel[day] = {}
        for code in CORE_FOUR:
            panel[day][code] = {
                "shares": str(1000 + 10 * n),
                "nav": "2",
                "aum": str(2000 + 20 * n),
                "share_unit": "shares", "nav_unit": "CNY/share",
                "source_url": "https://www.sse.com.cn/fake-fixture",
                "nav_source_url": "https://example.org/fake-nav-fixture",
                "published_at": f"{day}T20:00:00+08:00",
                "nav_published_at": f"{day}T21:00:00+08:00",
            }
    return panel


def denoms():
    return (
        {"date": DAYS[-1], "kind": "CSI300_ordinary_float_mv",
         "value": "42000", "unit": "CNY", "source_url": "https://www.csindex.com.cn/fixture",
         "published_at": f"{DAYS[-1]}T20:00:00+08:00"},
        {"date": DAYS[-1], "kind": "CSI300_free_float_mv",
         "value": "84000", "unit": "CNY", "source_url": "https://www.csindex.com.cn/fixture",
         "published_at": f"{DAYS[-1]}T20:00:00+08:00"},
    )


def test_original_fixed_four_metrics_and_three_percent_is_only_alert():
    ordinary, free = denoms()
    out = calculate(sample_panel(), DAYS, DAYS[-1], decision_cutoff=CUTOFF,
                    ordinary_float_mv=ordinary, free_float_mv=free)
    assert out["codes"] == list(CORE_FOUR)
    assert Decimal(out["daily_net_creation_proxy_cny"]) == 80
    assert Decimal(out["fund_aum_cny"]) == 8400
    assert Decimal(out["ordinary_float_coverage_ratio"]) == Decimal("0.2")
    assert Decimal(out["free_float_coverage_ratio"]) == Decimal("0.1")
    assert Decimal(out["five_day"]["net_creation_cny_daily_sum"]) == 400
    assert Decimal(out["five_day"]["net_creation_cny_endpoint_nav"]) == 400
    assert Decimal(out["five_day"]["net_creation_pct_initial_aum"]) == Decimal("0.05")
    assert out["five_day"]["hypothetical_abs_3pct_alert"] is True
    assert out["five_day"]["threshold_is_unvalidated"] is True
    assert out["investor_identity_attributable"] is False
    assert out["trade_signal_authorized"] is False


def test_distinguish_sum_of_daily_NAV_from_endpoint_NAV():
    panel = sample_panel()
    for n, day in enumerate(DAYS):
        for code in CORE_FOUR:
            panel[day][code]["nav"] = str(2 + n * Decimal("0.1"))
            panel[day][code]["aum"] = None
    x = calculate(panel, DAYS, DAYS[-1], decision_cutoff=CUTOFF)
    assert Decimal(x["five_day"]["net_creation_cny_endpoint_nav"]) == Decimal("500")
    assert Decimal(x["five_day"]["net_creation_cny_daily_sum"]) == Decimal("460")
    assert x["aum_is_partially_estimated"] is True


def test_do_not_extend_four_in_place_or_attach_CSI300_cap_to_mixed_index():
    panel = sample_panel()
    with pytest.raises(DataGateError, match="original four-ETF"):
        calculate(panel, DAYS, DAYS[-1], basket=CORE_FOUR[:3])
    with pytest.raises(DataGateError, match="CSI300-only"):
        calculate(panel, DAYS, DAYS[-1], basket=CORE_FOUR,
                  basket_name="expanded_nine", ordinary_float_mv=denoms()[0])


def test_unpublished_NAV_cannot_enter_0830_report():
    panel = sample_panel()
    with pytest.raises(DataGateError, match="not public"):
        calculate(panel, DAYS, DAYS[-1], decision_cutoff="2026-10-26T17:30:00+08:00")


def test_no_imputation_for_missing_fund_or_corporate_action():
    panel = sample_panel()
    del panel[DAYS[-2]][CORE_FOUR[0]]
    with pytest.raises(DataGateError, match="missing ETF"):
        calculate(panel, DAYS, DAYS[-1], decision_cutoff=CUTOFF)
    panel = sample_panel()
    panel[DAYS[-1]][CORE_FOUR[0]]["corporate_action"] = "split"
    with pytest.raises(DataGateError, match="split/consolidation"):
        calculate(panel, DAYS, DAYS[-1], decision_cutoff=CUTOFF)


def test_no_ratio_when_denominator_unavailable():
    out = calculate(sample_panel(), DAYS, DAYS[-1], decision_cutoff=CUTOFF)
    assert out["ordinary_float_coverage_ratio"] is None
    assert out["free_float_coverage_ratio"] is None
    assert out["daily_net_creation_proxy_cny"] is not None


def test_denominator_date_and_type_cannot_mismatch():
    ordinary, _ = denoms()
    ordinary["date"] = "2026-10-23"
    with pytest.raises(DataGateError, match="date/type mismatch"):
        calculate(sample_panel(), DAYS, DAYS[-1], decision_cutoff=CUTOFF,
                  ordinary_float_mv=ordinary)


def test_5d_requires_six_complete_sessions():
    out = calculate(sample_panel(), DAYS[:2], DAYS[1], decision_cutoff=CUTOFF)
    assert out["five_day"] is None
    assert Decimal(out["daily_net_creation_proxy_cny"]) == 80
