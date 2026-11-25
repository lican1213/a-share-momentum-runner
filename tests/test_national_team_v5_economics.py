"""Economic audit regression on a real frozen ledger, without a live feed."""
import copy
import json
from pathlib import Path

import pytest

from national_team.left_entry_v4 import digest
from scripts.audit_national_team_v5_economics import audit


RECORD = Path(__file__).resolve().parents[1] / (
    "records/national_team_paper_accounts_v5/2026-11-25/45485167060-a1.json"
)


def snapshot():
    return json.loads(RECORD.read_text(encoding="utf-8"))


def resign(obj):
    obj.pop("snapshot_sha256")
    obj["snapshot_sha256"] = digest(obj)
    return obj


def test_real_ledger_economic_attribution():
    result = audit(snapshot())
    assert (result["filled"], result["closed"], result["open_positions"]) == (26, 24, 2)
    assert result["skips"]["ENTRY_OHLC_MISSING_NO_RETROSPECTIVE_FILL"] == 20
    assert sum(result["skips"].values()) == 42
    assert result["groups"]["all"]["wins"] == 12
    assert result["groups"]["all"]["net"] == "-541.52"
    assert result["groups"]["version:EXP-0017"]["net"] == "-575.09"
    assert result["groups"]["exit:GAP_STOP_AT_OPEN"]["net"] == "-298.35"
    assert result["same_day_reentries"] == [
        {"arm": "R_BOUNCE", "stock": "601728", "session": "2026-11-23", "net_cny": "-298.35"}
    ]


def test_refuse_tamper_and_duplicate_even_with_new_hash():
    obj = snapshot()
    obj["accounts"]["SHALLOW_DIP"]["closed_trades"][0]["net_pnl_cny"] = "999"
    with pytest.raises(ValueError, match="hash mismatch"):
        audit(obj)
    obj = snapshot()
    trades = obj["accounts"]["SHALLOW_DIP"]["closed_trades"]
    trades.append(copy.deepcopy(trades[0]))
    with pytest.raises(ValueError, match="duplicate or unmatched"):
        audit(resign(obj))


def test_missing_benchmark_never_becomes_zero():
    obj = snapshot()
    for account in obj["accounts"].values():
        for trade in account["closed_trades"]:
            trade["s0_equal_capital_pnl_cny"] = None
            trade["excess_s0_equal_capital_cny"] = None
    result = audit(resign(obj))["groups"]["all"]
    assert result["paired"] == 0
    assert result["benchmark"] is None and result["excess"] is None
    assert result["net"] == "-541.52"


def test_no_broker_orders_or_missing_arm_allowed():
    obj = snapshot()
    obj["broker_orders"] = ["not allowed"]
    with pytest.raises(ValueError, match="research-only"):
        audit(resign(obj))
    obj = snapshot()
    del obj["accounts"]["EARLY_ENTRY"]
    with pytest.raises(ValueError, match="incomplete"):
        audit(resign(obj))
