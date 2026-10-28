"""No repeat paper-trade events from repeated runs of the same trade date."""
from national_team.paper_events import freeze_watch

def fixture():
    return {
        "status":"INDEX_PROXY_RESEARCH_WATCHLIST",
        "funding_date":"2026-10-27",
        "event_first_public_no_earlier_than":"2026-10-28T22:05:00+08:00",
        "research_ranking":{
            "source_kind":"CSI300_LATEST_INDEX_WEIGHT_PROXY_NOT_ETF_PCF",
            "data_scope":"FOUR_ETF_DATED_SHARE_FLOW",
            "observed_funds":["510300","510310","510330","159919"],
            "topn_pool_is_partial":True,
            "candidates":[
                {"symbol":"600036","relative_strength20":"0.05","signed_exposure_over_adv20":"0.04"},
                {"symbol":"600519","relative_strength20":"0.02","signed_exposure_over_adv20":"0.03"},
                {"symbol":"601166","relative_strength20":"0.09","signed_exposure_over_adv20":"0.02"}
            ]}
    }

def test_signal_is_event_frozen_after_actual_data_arrival():
    a=freeze_watch(fixture(),source_path="records/watch/A.json",model_sha="sha1")
    assert len(a["events"])==2
    first=a["events"][0]
    assert first["candidate_symbols"]==["600036","600519","601166"]
    assert first["funding_underlying_day"]=="2026-10-27"
    assert first["first_public_at"].startswith("2026-10-28T22:05")
    assert first["ETF_PCF_verified"] is False
    assert first["broker_trades_authorized"] is False
    assert a["events"][1]["candidate_symbols"][0]=="601166"

def test_same_economic_event_reused_across_runs_gets_same_id():
    a=freeze_watch(fixture(),source_path="watch/old.json",model_sha="v1")
    b=freeze_watch(fixture(),source_path="watch/new.json",model_sha="v2")
    assert [e["id"] for e in a["events"]]==[e["id"] for e in b["events"]]

def test_negative_flow_or_stale_funding_never_frozen_as_optimistic_long():
    src=fixture();src["research_ranking"]["candidates"]=[]
    assert freeze_watch(src,source_path="x",model_sha="v1")["status"]=="NO_POSITIVE_RESEARCH_EVENT"
    src=fixture();src["funding_date"]="2026-10-15"
    assert freeze_watch(src,source_path="x",model_sha="v1")["status"]=="STALE_FUNDING_NOT_FROZEN"
