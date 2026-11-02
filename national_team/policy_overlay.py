"""EXP-0015: point-in-time official-policy overlay for the existing V5 ETF router.

Borrow AIHOT's source-tiered collection and event deduplication, not its web
stack or LLM scoring. Policy adds evidence; it never opens a broker order.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

BJ = timezone(timedelta(hours=8))
WINDOW_DAYS = 7
SOURCES = (
    ("PBC_RSS", "https://www.pbc.gov.cn/goutongjiaoliu/113456/2986536/index.html"),
    ("CSRC_NEWS", "https://www.csrc.gov.cn/searchList/a1a078ee0bc54721ab6b148884c784a8"),
    ("GOV_POLICY", "https://sousuo.www.gov.cn/search-gov/data"),
)

DIRECT = re.compile(
    r"互换便利|股票回购增持再贷款|回购增持再贷款|中长期资金.{0,6}入市|"
    r"稳住股市|稳定股市|资本市场.{0,6}(稳定|稳市|支持)|"
    r"(增持|投资).{0,9}(股票ETF|股票型ETF)|"
    r"(股票ETF|股票型ETF).{0,9}(增持|投资)|"
    r"(汇金|诚通|国新).{0,10}(增持|买入|回购)"
)
EASING = re.compile(
    r"降准|降息|下调.{0,12}(存款准备金率|政策利率|贷款市场报价利率)|"
    r"加大.{0,8}(逆周期调节|货币政策力度)|"
    r"(增发|加快发行).{0,8}(特别国债|专项债)"
)
TIGHTENING = re.compile(
    r"上调.{0,12}(存款准备金率|政策利率)|"
    r"收紧.{0,10}(证券融资|股票融资|市场流动性)|"
    r"(降低|限制).{0,8}权益投资比例"
)
SECTOR = re.compile(r"半导体|集成电路|人工智能|房地产|新能源汽车|光伏|医药")
ACTION = re.compile(r"启动|创设|出台|落地|实施|操作|增持|扩围|增量|扩大|加力|推出|印发|开展|明确")


def _fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ASharePolicyResearch/1.0)",
                                "Accept": "application/json, application/xml, text/xml, */*"})
    with urlopen(req, timeout=12) as response:
        return response.read(1_500_001)[:1_500_000]


def _source_url(source):
    url = dict(SOURCES)[source]
    if source == "CSRC_NEWS":
        return url + "?" + urlencode({
            "_isAgg": "true", "_isJson": "true", "_pageSize": 25,
            "_template": "index", "_rangeTimeGte": "", "_channelName": "", "page": 1,
        })
    if source == "GOV_POLICY":
        return url + "?" + urlencode({
            "t": "zhengcelibrary_gw", "q": "", "sort": "pubtime",
            "sortType": 1, "searchfield": "title", "p": 1, "n": 30, "type": "gwyzcwjk",
        })
    return url


def _clean(value):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", " ", str(value or ""))).strip()


def _canonical_url(url, host):
    url = str(url or "").strip()
    if url.startswith("/"):
        url = urljoin("https://" + host + "/", url)
    parsed = urlsplit(url)
    if parsed.hostname not in (host, "www." + host) or parsed.scheme not in ("http", "https"):
        return None
    return urlunsplit(("https", "www." + host, parsed.path, "", ""))


def _read_csrc(raw):
    payload = json.loads(raw.decode("utf-8-sig"))
    rows = payload["data"]["results"]
    if not isinstance(rows, list):
        raise ValueError("CSRC results is not a list")
    for row in rows:
        url = _canonical_url(row.get("url"), "csrc.gov.cn")
        if url and row.get("title") and row.get("publishedTimeStr"):
            yield {
                "title": row["title"], "summary": row.get("content") or row.get("contentHtml") or "",
                "url": url, "published": row["publishedTimeStr"],
            }


def _read_gov(raw):
    payload = json.loads(raw.decode("utf-8-sig"))
    if str(payload.get("code")) != "200":
        raise ValueError("GOV returned non-200 code")
    rows = payload["searchVO"]["listVO"]
    if not isinstance(rows, list):
        raise ValueError("GOV listVO is not a list")
    for row in rows:
        url = _canonical_url(row.get("url"), "gov.cn")
        if url and row.get("title") and row.get("pubtimeStr"):
            yield {
                "title": row["title"], "summary": row.get("summary") or "",
                "url": url, "published": str(row["pubtimeStr"]).replace(".", "-"),
            }


def _read_pbc(raw):
    root = ET.fromstring(raw)
    items = root.findall(".//item")
    if not items:
        # Atom, although the official feed is normally RSS.
        items = [node for node in root if node.tag.rsplit("}", 1)[-1] == "entry"]
    if not items:
        raise ValueError("PBC feed contained no items")
    for node in items:
        fields = {}
        for child in node:
            key = child.tag.rsplit("}", 1)[-1].lower()
            fields[key] = child.attrib.get("href") or child.text or ""
        url = _canonical_url(fields.get("link") or fields.get("guid"), "pbc.gov.cn")
        if url and fields.get("title"):
            yield {
                "title": fields["title"], "summary": fields.get("description") or fields.get("summary") or "",
                "url": url,
                "published": (fields.get("pubdate") or fields.get("published")
                              or fields.get("updated") or fields.get("date")),
            }


PARSERS = {"PBC_RSS": _read_pbc, "CSRC_NEWS": _read_csrc, "GOV_POLICY": _read_gov}


def _published(value, observed):
    """Date-only stays date-only; absent PBC date means first-observed only."""
    if not value:
        return observed.date().isoformat(), None, "FIRST_OBSERVED_ONLY"
    raw = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return date.fromisoformat(raw).isoformat(), None, "DATE_ONLY"
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        stamp = parsedate_to_datetime(raw)
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=BJ)
    stamp = stamp.astimezone(BJ)
    return stamp.date().isoformat(), stamp.isoformat(), "TIMESTAMP"


def classify(title, summary):
    title = _clean(title)
    excerpt = _clean(summary)[:240]
    body = title + " " + excerpt
    if TIGHTENING.search(title):
        return ("MARKET_TIGHTENING", "PRESSURE", 1)
    if DIRECT.search(title) or (DIRECT.search(excerpt) and ACTION.search(title)):
        return ("CAPITAL_MARKET_SUPPORT", "SUPPORT", 2)
    if EASING.search(title) or (EASING.search(excerpt) and ACTION.search(title)):
        return ("MACRO_EASING", "SUPPORT", 1)
    if SECTOR.search(title) and ACTION.search(body):
        return ("SECTOR_POLICY", "SECTOR", 0)
    return None


def _title_key(title):
    return re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]", "", title).lower()


def collect_snapshot(*, now, fetcher=None, prior_first_seen=None):
    """One immutable observation with independent source error reporting."""
    observed = datetime.fromisoformat(now)
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("capture must have a timezone")
    captured = observed.astimezone(BJ).isoformat()
    prior_first_seen = prior_first_seen or {}
    fetcher = fetcher or _fetch
    group, health = {}, []
    for source, _ in SOURCES:
        status = {"source": source, "tier": "T1_OFFICIAL", "status": "FAILED",
                  "fetched": 0, "relevant": 0, "error": None}
        try:
            rows = list(PARSERS[source](fetcher(_source_url(source))))
            if not rows:
                raise ValueError("no parseable entries")
            status["fetched"] = len(rows)
            for row in rows:
                tagged = classify(row["title"], row["summary"])
                if tagged is None:
                    continue
                day, instant, precision = _published(row["published"], observed.astimezone(BJ))
                # Only classify announcements that already have a release date.
                if day > observed.astimezone(BJ).date().isoformat():
                    continue
                status["relevant"] += 1
                key = _title_key(_clean(row["title"]))
                if not key:
                    continue
                event = group.get(key)
                first_seen = min(captured, prior_first_seen.get(row["url"], captured))
                if event is None:
                    event = {
                        "event_id": "POL_" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                        "title": _clean(row["title"]),
                        "published_date": day, "published_at_bj": instant,
                        "publication_precision": precision,
                        "first_observed_at_bj": first_seen,
                        "policy_type": tagged[0], "direction": tagged[1],
                        "strength": tagged[2],
                        "url": row["url"], "sources": [source],
                        "evidence_urls": [row["url"]],
                    }
                    group[key] = event
                else:
                    event["first_observed_at_bj"] = min(event["first_observed_at_bj"], first_seen)
                    if source not in event["sources"]:
                        event["sources"].append(source)
                    if row["url"] not in event["evidence_urls"]:
                        event["evidence_urls"].append(row["url"])
            status["status"] = "OK"
        except (ValueError, TypeError, KeyError, UnicodeError, OSError, ET.ParseError) as exc:
            status["error"] = f"{type(exc).__name__}: {str(exc)[:160]}"
        health.append(status)
    events = sorted(group.values(), key=lambda x: (x["published_date"], x["strength"]), reverse=True)
    snapshot = {
        "schema": 1, "experiment_id": "EXP-0015",
        "version": "NT_OFFICIAL_POLICY_OVERLAY",
        "captured_at_bj": captured, "sources": health,
        "source_health": ("OK" if all(s["status"] == "OK" for s in health)
                          else "PARTIAL" if any(s["status"] == "OK" for s in health)
                          else "UNAVAILABLE"),
        "events": events[:80], "source_tier": "T1_OFFICIAL",
        "no_broker_orders": True,
    }
    snapshot["snapshot_sha256"] = hashlib.sha256(
        json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return snapshot


def load_prior_first_seen(root):
    """Re-use first *observed* time from prior immutable policy snapshots."""
    import json
    from pathlib import Path
    first = {}
    for path in sorted(Path(root).glob("*/*.json"))[-120:]:
        try:
            items = json.loads(path.read_text(encoding="utf-8")).get("events", [])
            for item in items:
                for url in item.get("evidence_urls", [item["url"]]):
                    old = first.get(url, item["first_observed_at_bj"])
                    first[url] = min(old, item["first_observed_at_bj"])
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return first


def summarize(snapshot, *, now, funding_day, etf_flow_active):
    """Attach policy to ETF funding without changing the V5 admission rule."""
    absent = {
        "experiment_id": "EXP-0015", "status": "NOT_COLLECTED",
        "source_health": "NOT_COLLECTED", "snapshot_sha256": None,
        "support_count": 0, "matched_funding_event_ids": [],
        "recent_event_ids": [], "top_events": [], "changes_admission": False,
        "trade_authorized": False,
    }
    if snapshot is None:
        return absent
    observed = datetime.fromisoformat(now).astimezone(BJ)
    capture = datetime.fromisoformat(snapshot["captured_at_bj"]).astimezone(BJ)
    if capture > observed:
        return {**absent, "status": "POLICY_SNAPSHOT_IN_FUTURE",
                "source_health": snapshot.get("source_health", "UNKNOWN")}
    recent = []
    for event in snapshot.get("events", []):
        day = date.fromisoformat(event["published_date"])
        first = datetime.fromisoformat(event["first_observed_at_bj"]).astimezone(BJ)
        pub = event.get("published_at_bj")
        if (first > observed or (pub and datetime.fromisoformat(pub).astimezone(BJ) > observed)
                or not (0 <= (observed.date() - day).days <= WINDOW_DAYS)):
            continue
        recent.append(event)
    support = [e for e in recent if e["direction"] == "SUPPORT"]
    matched = [e for e in support if
               e["publication_precision"] != "FIRST_OBSERVED_ONLY" and
               0 <= (date.fromisoformat(funding_day) -
                     date.fromisoformat(e["published_date"])).days <= WINDOW_DAYS]
    if snapshot.get("source_health") == "UNAVAILABLE":
        status = "POLICY_SOURCES_UNAVAILABLE"
    elif etf_flow_active and matched:
        status = "POLICY_ETF_RESONANCE"
    elif etf_flow_active:
        status = "ETF_FLOW_WITHOUT_POLICY_MATCH"
    elif support:
        status = "POLICY_WATCH_WITHOUT_ETF_FLOW"
    else:
        status = "NO_RECENT_SUPPORT_POLICY"
    return {
        "experiment_id": "EXP-0015", "status": status,
        "source_health": snapshot.get("source_health", "UNKNOWN"),
        "snapshot_sha256": snapshot.get("snapshot_sha256"),
        "support_count": len(support),
        "matched_funding_event_ids": [e["event_id"] for e in matched],
        "recent_event_ids": [e["event_id"] for e in recent],
        "top_events": [{k: e[k] for k in ("event_id", "title", "policy_type", "direction",
                                        "strength", "published_date", "url")}
                       for e in recent[:6]],
        "changes_admission": False, "trade_authorized": False,
        "not_a_policy_implied_etf_purchase": True,
    }
