"""Real snapshot and adversarial evidence cases."""
import json
from decimal import Decimal
from pathlib import Path

import pytest

from national_team.core_flow_factors import DataGateError
from scripts.research_national_team_withdrawal import diagnose

RECORD = Path(__file__).resolve().parents[1] / (
    "records/national_team_merged/2026-11-25/45555469588-a1.json"
)


def snapshot():
    return json.loads(RECORD.read_text(encoding="utf-8"))


def test_real_record_reversal_not_confirmed_exit():
    report = diagnose(snapshot())
    assert report["session"] == "2026-11-24"
    assert Decimal(report["net_cny_by_window"]["1"]) == Decimal("-3167860950")
    assert Decimal(report["net_cny_by_window"]["5"]) == Decimal("80447523840")
    assert report["daily"][-1]["negative_funds"] == 3
    assert report["raw_flow_pattern"] == "REDEMPTION_AGAINST_POSITIVE_5D"
    assert any(x["code"] == "159919" and x["session"] == "2026-11-20"
               for x in report["anomaly_review"])
    assert report["withdrawal_confirmed"] is False
    assert report["investor_identity_attributable"] is False
    assert report["trade_authorized"] is False and report["broker_orders"] == []


def test_late_capture_cannot_backdate_decision():
    with pytest.raises(DataGateError, match="not available"):
        diagnose(snapshot(), cutoff="2026-11-24T15:00:00+08:00")


@pytest.mark.parametrize("case", ["missing", "wrong_unit", "conflict", "stale",
                                  "duplicate_day", "future_row", "old_timestamp",
                                  "missing_path", "bad_number", "factor_tamper", "missing_day"])
def test_fail_closed(case):
    obj = snapshot()
    event = obj["funding_event"]
    row = obj["observations_by_date"]["2026-11-24"]["159919"]
    if case == "missing":
        del obj["observations_by_date"]["2026-11-24"]["159919"]
    elif case == "wrong_unit":
        obj["unit"] = "lots"
    elif case == "conflict":
        obj["conflicts"] = ["conflicting quote"]
    elif case == "stale":
        event["latest_available_trading_day"] = "2026-11-25"
    elif case == "duplicate_day":
        event["history_sessions"].append("2026-11-24")
    elif case == "future_row":
        row["shares_first_observed_at"] = "2026-11-26T09:30:00+08:00"
    elif case == "old_timestamp":
        row["shares_first_observed_at"] = "2026-11-23T09:30:00+08:00"
    elif case == "missing_path":
        row["shares_source_path"] = ""
    elif case == "bad_number":
        row["shares"] = "NaN"
    elif case == "factor_tamper":
        event["four_etf_factor"]["daily_net_creation_proxy_cny"] = "999"
    elif case == "missing_day":
        del obj["observations_by_date"]["2026-11-20"]
    with pytest.raises(DataGateError):
        diagnose(obj)
