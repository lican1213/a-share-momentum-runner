"""Unit-level adversarial merge: no historical source rewrites or fake PTI."""
from national_team.record_merge import merge_snapshot_records
from national_team.event_pipeline import reconcile_funding_snapshot
from national_team.core_flow_factors import CORE_FOUR

CAP="2026-10-28T22:00:00+08:00"
DAYS=["2026-10-19","2026-10-20","2026-10-21","2026-10-22","2026-10-23","2026-10-26"]

def sources():
    sse={d:{c:{"shares":str(100000000+i*100000),"nav":"4.0"}
              for c in CORE_FOUR[:3]} for i,d in enumerate(DAYS)}
    szse={d:{"159919":{"shares":str(100000000+i*50000),"nav":"3.0"}}
              for i,d in enumerate(DAYS)}
    return [("source-SSE",{"run_id":"SSE-run","asof_requested":"2026-10-28",
                          "capture_completed_beijing":"2026-10-28T20:00:00+08:00",
                          "observations_by_date":sse}),
            ("source-SZSE",{"run_id":"SZSE-run","asof_requested":"2026-10-28",
                          "capture_completed_beijing":"2026-10-28T21:00:00+08:00",
                          "observations_by_date":szse})]

def test_combine_independent_dates_and_recover_full_four_cash_flow():
    m=merge_snapshot_records(sources(),"2026-10-28",at=CAP)
    assert m["conflicted_date_code_pairs"]==0
    assert len(m["sources_used"])==2
    r=reconcile_funding_snapshot(m,DAYS)
    assert r["status"]=="FULL_FOUR_ETF_SHARES_NAV_OBSERVED_RESEARCH"
    assert r["four_etf_factor"]["daily_net_creation_proxy_cny"]=="1350000.0"
    assert r["first_available_at"]==CAP
    assert r["four_etf_factor"]["investor_identity_attributable"] is False

def test_conflict_censors_instead_of_selecting_convenient_last_value():
    entries=sources()
    extra={"run_id":"conflict","asof_requested":"2026-10-28",
           "capture_completed_beijing":"2026-10-28T21:30:00+08:00",
           "observations_by_date":{"2026-10-23":{"510300":{"shares":"999999999","nav":"4"}}}}
    m=merge_snapshot_records(entries+[("contradiction",extra)],"2026-10-28",at=CAP)
    assert m["conflicted_date_code_pairs"]==1
    assert "510300" not in m["observations_by_date"]["2026-10-23"]
    r=reconcile_funding_snapshot(m,DAYS)
    assert r["four_etf_factor"] is None
    assert "510300" in r["missing_by_day"]["2026-10-23"]

def test_no_undated_szse_list_snapshot_is_promoted_to_historical_date():
    a=sources()[:1]
    a[0][1]["latest_undated_szse_snapshot"]={"fund_code":"159919","shares":"10396116676"}
    m=merge_snapshot_records(a,"2026-10-28",at=CAP)
    assert "159919" not in m["observations_by_date"][DAYS[-1]]
    assert m["undated_SZSE_snapshots_excluded"] is True
