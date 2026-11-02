"""EXP-0015: official policy capture, dedup, as-of and non-gating regression."""
from __future__ import annotations

import json
from datetime import datetime

from national_team.policy_overlay import (
    collect_snapshot, summarize, classify, load_prior_first_seen,
)
from national_team.event_router_v5 import route


AT = "2026-11-02T18:01:00+08:00"
TITLE = "证监会等部门联合印发推动中长期资金入市实施方案"


def sources(pbc=None, csrc=None, gov=None):
    pbc = pbc or (
        "<rss><channel><item><title>央行启动证券基金保险公司互换便利</title>"
        "<link>http://www.pbc.gov.cn/goutongjiaoliu/113456/113469/xxx/index.html</link>"
        "<pubDate>Fri, 30 Oct 2026 09:00:00 +0800</pubDate>"
        "<description>资本市场支持工具已启动</description></item></channel></rss>"
    )
    csrc = csrc or json.dumps({"data": {"results": [
        {"title": TITLE, "url": "/csrc/c100028/c123456/content.shtml",
         "publishedTimeStr": "2026-11-02 10:05:00", "content": "支持长钱入市"}
    ]}}, ensure_ascii=False)
    gov = gov or json.dumps({"code": 200, "searchVO": {"listVO": [
        {"title": TITLE, "url": "https://www.gov.cn/zhengce/202611/content_1234.htm",
         "pubtimeStr": "2026.11.02", "summary": "推动股票市场资金稳定"}
    ]}}, ensure_ascii=False)

    def fetch(url):
        if "pbc.gov.cn" in url:
            return pbc.encode()
        if "csrc.gov.cn" in url:
            return csrc.encode()
        if "sousuo.www.gov.cn" in url:
            return gov.encode()
        raise AssertionError("unexpected official source " + url)
    return fetch


def test_official_three_sources_deduplicate_by_event_and_preserve_first_seen():
    snap = collect_snapshot(now=AT, fetcher=sources())
    assert snap["source_health"] == "OK"
    assert len(snap["events"]) == 2
    shared = next(e for e in snap["events"] if e["title"] == TITLE)
    assert shared["sources"] == ["CSRC_NEWS", "GOV_POLICY"]
    assert shared["policy_type"] == "CAPITAL_MARKET_SUPPORT"
    assert len(shared["evidence_urls"]) == 2
    assert shared["publication_precision"] == "TIMESTAMP"
    assert shared["first_observed_at_bj"] == AT
    assert all(e["direction"] == "SUPPORT" for e in snap["events"])


def test_policy_plus_etf_flow_resonance_but_never_a_broker_gate():
    snap = collect_snapshot(now=AT, fetcher=sources())
    together = summarize(snap, now="2026-11-02T18:05:00+08:00",
                         funding_day="2026-11-02", etf_flow_active=True)
    assert together["status"] == "POLICY_ETF_RESONANCE"
    assert len(together["matched_funding_event_ids"]) == 2
    assert together["changes_admission"] is False
    assert together["trade_authorized"] is False
    policy_only = summarize(snap, now="2026-11-02T18:05:00+08:00",
                            funding_day="2026-11-02", etf_flow_active=False)
    assert policy_only["status"] == "POLICY_WATCH_WITHOUT_ETF_FLOW"


def test_cannot_use_future_publication_or_snapshot_and_dated_only_not_intraday():
    snap = collect_snapshot(now=AT, fetcher=sources())
    assert summarize(snap, now="2026-11-02T17:55:00+08:00",
                     funding_day="2026-11-02", etf_flow_active=True)["status"] == (
        "POLICY_SNAPSHOT_IN_FUTURE")
    for event in snap["events"]:
        if event["publication_precision"] == "DATE_ONLY":
            assert event["published_at_bj"] is None
    future = json.loads(json.dumps(snap))
    future["events"][0]["first_observed_at_bj"] = "2026-11-03T09:00:00+08:00"
    result = summarize(future, now="2026-11-02T18:05:00+08:00",
                       funding_day="2026-11-02", etf_flow_active=True)
    assert future["events"][0]["event_id"] not in result["recent_event_ids"]


def test_policy_after_funding_not_backdated_as_funding_confirmation():
    snap = collect_snapshot(now=AT, fetcher=sources())
    result = summarize(snap, now="2026-11-02T18:05:00+08:00",
                       funding_day="2026-10-30", etf_flow_active=True)
    ids = result["matched_funding_event_ids"]
    assert len(ids) == 1
    assert next(e for e in snap["events"] if e["event_id"] == ids[0])["published_date"] == (
        "2026-10-30")


def test_failed_independent_feed_is_visible_not_a_hard_veto():
    def partial(url):
        if "pbc.gov.cn" in url:
            raise TimeoutError("PBC timed out")
        return sources()(url)
    snap = collect_snapshot(now=AT, fetcher=partial)
    assert snap["source_health"] == "PARTIAL"
    assert len(snap["events"]) == 1
    assert snap["sources"][0]["status"] == "FAILED"
    assert summarize(snap, now="2026-11-02T18:05:00+08:00",
                     funding_day="2026-11-02", etf_flow_active=True)["status"] == (
        "POLICY_ETF_RESONANCE")
    failed = collect_snapshot(now=AT, fetcher=lambda url: (_ for _ in ()).throw(
        TimeoutError("all failed")))
    assert failed["source_health"] == "UNAVAILABLE"
    assert failed["events"] == []
    assert summarize(failed, now="2026-11-02T18:05:00+08:00",
                     funding_day="2026-11-02", etf_flow_active=True)["status"] == (
        "POLICY_SOURCES_UNAVAILABLE")


def test_generic_regulation_is_not_mistaken_for_injection_and_no_free_probability():
    assert classify("证监会发布违规转让证券案件行政处罚实施规则", "") is None
    assert classify("降低金融机构权益投资比例", "") == (
        "MARKET_TIGHTENING", "PRESSURE", 1)
    assert classify("工信部印发支持半导体产业发展的通知", "") == (
        "SECTOR_POLICY", "SECTOR", 0)


def test_prior_first_seen_is_reused_from_immutable_archives(tmp_path):
    path = tmp_path / "2026-11-01" / "run.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps({"events": [{
        "url": "https://www.csrc.gov.cn/csrc/c100028/c123456/content.shtml",
        "evidence_urls": ["https://www.csrc.gov.cn/csrc/c100028/c123456/content.shtml"],
        "first_observed_at_bj": "2026-11-01T18:05:00+08:00"
    }]}), encoding="utf-8")
    prior = load_prior_first_seen(tmp_path)
    snap = collect_snapshot(now=AT, fetcher=sources(), prior_first_seen=prior)
    event = next(e for e in snap["events"] if e["title"] == TITLE)
    assert event["first_observed_at_bj"] == "2026-11-01T18:05:00+08:00"


def test_original_etf_dispatch_unchanged_when_policy_is_present(tmp_path):
    def write(root, name, data):
        p = root / "2026-11-02" / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data), encoding="utf-8")
    v3, watch, freeze, outcomes = [tmp_path / x for x in ("v3", "watch", "freeze", "outcomes")]
    write(v3, "v3.json", {
        "method": {"codes": ["510300", "510310", "510330", "159919"]},
        "daily": [{"date": "2026-11-02", "market_down": True,
                   "share_proxy_event": True, "net_creation_1d_cny": 100,
                   "net_creation_5d_cny": 300}],
        "data_quality": {"last_full_four_share_day": "2026-11-02"},
    })
    write(watch, "watch.json", {
        "funding_date": "2026-11-02", "collector_capture_time": AT,
        "candidate_pool_pre_filter": ["600002"],
    })
    snap = collect_snapshot(now=AT, fetcher=sources())
    before = route(v3, watch, freeze, outcomes, now="2026-11-02T18:05:00+08:00")
    after = route(v3, watch, freeze, outcomes, now="2026-11-02T18:05:00+08:00",
                  policy_snapshot=snap)
    for key in ("status", "dispatcher", "selected_policy", "broker_orders", "trade_authorized"):
        assert before[key] == after[key]
    assert after["status"] == "NEW_FUNDING_EVENT"
    assert after["policy_overlay"]["status"] == "POLICY_ETF_RESONANCE"
