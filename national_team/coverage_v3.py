"""EXP-0010: fixed-four CSI300 ETF coverage and reproducible event replay.

Retrospective ETF-wide research, never investor-identity attribution or brokerage orders.
No imputation of missing daily NAV or index market-value denominator.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import Counter
from datetime import datetime
from pathlib import Path

from national_team.core_flow_factors import CORE_FOUR

VERSION = "NT-V3-EXP-0010-v1"
HORIZONS = (5, 10, 20)
SHARES_SOURCE = "https://github.com/wwww1998/national-team-etf-flow/blob/main/_etf_shares_cache.json"
INDEX_SOURCE = "https://github.com/sky910140/financial-agent-takehome/blob/main/data/market/csi300.csv"
DENOM_KINDS = ("CSI300_ordinary_float_mv", "CSI300_free_float_mv")


def _num(value, label, *, positive=True):
    if isinstance(value, bool):
        raise ValueError(f"{label}: bool not permitted")
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        raise ValueError(f"{label}: missing/non-numeric") from None
    if not math.isfinite(number) or (positive and number <= 0) or (not positive and number < 0):
        raise ValueError(f"{label}: invalid nonfinite/sign")
    return number


def _day(value):
    text = str(value).strip()
    if len(text) == 8 and text.isdigit():
        return f"{text[:4]}-{text[4:6]}-{text[6:]}"
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        return text
    raise ValueError(f"invalid trade day: {value!r}")


def _timestamp(value, label):
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise ValueError(f"{label}: invalid ISO publication timestamp") from None
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError(f"{label}: timezone required")
    return t


def read_shares(path):
    """Upstream cache has historical shares but lacks per-day first-public times."""
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    raw = data.get("shares", {})
    if not isinstance(raw, dict):
        raise ValueError("upstream shares must be date-keyed mapping")
    result = {}
    for day, funds in raw.items():
        if not isinstance(funds, dict):
            continue
        if any(code not in funds for code in CORE_FOUR):
            continue  # missing 159919 cannot be treated as a zero or filled from yesterday
        d = _day(day)
        result[d] = {c: _num(funds[c], f"{d}:{c} shares") for c in CORE_FOUR}
    return result


def read_prices(path):
    result = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            day = _day(row["date"])
            if day in result:
                raise ValueError(f"duplicate index close {day}")
            result[day] = _num(row["close"], f"{day} index close")
    if not result:
        raise ValueError("no index closes")
    return result


def read_nav(path):
    """Expected schema: {YYYY-MM-DD: {ETF: {nav,source_url,published_at}}}.

    A retrospective NAV with no dated publication fields may be used for arithmetic,
    but it never passes PIT validation; backfilled data must be visibly labelled.
    """
    if path is None:
        return {}
    raw = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    raw = raw.get("nav_by_date", raw)
    if not isinstance(raw, dict):
        raise ValueError("nav_by_date must be an object")
    nav = {}
    for date, funds in raw.items():
        if not isinstance(funds, dict):
            continue
        d = _day(date)
        nav[d] = {}
        for code in CORE_FOUR:
            if code not in funds:
                continue
            item = funds[code]
            if not isinstance(item, dict):
                item = {"nav": item}
            nav[d][code] = {
                "nav": _num(item.get("nav"), f"{d}:{code} NAV"),
                "source_url": item.get("source_url"),
                "published_at": item.get("published_at"),
                "corporate_action": item.get("corporate_action", "unknown"),
            }
    return nav


def read_denominators(path):
    """Exact-date, source-stamped CSV; *no* forward fill and no index-level proxy."""
    if path is None:
        return {}
    result = {}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            day, kind = _day(row["date"]), row["kind"]
            if kind not in DENOM_KINDS:
                raise ValueError(f"{day}: unsupported market cap kind {kind!r}")
            if row.get("index_code") != "000300.SH" or row.get("unit") != "CNY":
                raise ValueError(f"{day}: CSI300 index_code 000300.SH and CNY required")
            url = row.get("source_url") or ""
            if not url.startswith("https://"):
                raise ValueError(f"{day}: verified https source_url required")
            _timestamp(row.get("published_at"), f"{day} denominator")
            key = (day, kind)
            if key in result:
                raise ValueError(f"{day} {kind}: duplicate denominator")
            result[key] = {
                "value_cny": _num(row["value_cny"], f"{day} {kind}"),
                "published_at": row["published_at"],
                "source_url": url,
                "method": row.get("method", "unverified"),
            }
    return result


def _ratio_and_flow(date, dates, pos, shares, nav, caps):
    state = {"ordinary_float_coverage_ratio": None,
             "free_float_coverage_ratio": None,
             "coverage_change_1d": None, "coverage_change_5d": None,
             "net_creation_1d_cny": None, "net_creation_5d_cny": None,
             "ratio_pit_verified": False,
             "denominator_known_by_t_plus_1": False,
             "nav_not_known_late_by_t_plus_1": True,
             "ratio_status": "NAV_MISSING"}
    def per_day(j):
        d = dates[j]
        if d not in shares or d not in nav or any(c not in nav[d] or c not in shares[d] for c in CORE_FOUR):
            return None
        s = shares[d]
        n = nav[d]
        for code in CORE_FOUR:
            if n[code]["corporate_action"] in ("split", "consolidation", True):
                return None  # declared action invalidates inferred flow until reconciled
        return {"aum": sum(s[c] * n[c]["nav"] for c in CORE_FOUR),
                "nav": n, "shares": s}
    current = per_day(pos)
    if current is None:
        return state
    state["ratio_status"] = "DENOMINATOR_MISSING"
    ord_row = caps.get((date, DENOM_KINDS[0]))
    free_row = caps.get((date, DENOM_KINDS[1]))
    if ord_row:
        state["ordinary_float_coverage_ratio"] = current["aum"] / ord_row["value_cny"]
    if free_row:
        state["free_float_coverage_ratio"] = current["aum"] / free_row["value_cny"]
    state["ratio_status"] = "RATIO_RETROSPECTIVE" if ord_row else "DENOMINATOR_MISSING"
    def action_suspected(cur, before):
        return any(abs(cur["shares"][c] / before["shares"][c] - 1) > .30
                   and abs(cur["nav"][c]["nav"] / before["nav"][c]["nav"] - 1) > .20
                   and abs((cur["shares"][c] / before["shares"][c]) *
                           (cur["nav"][c]["nav"] / before["nav"][c]["nav"]) - 1) < .18
                   for c in CORE_FOUR)
    if pos >= 1:
        prev = per_day(pos - 1)
        if prev and not action_suspected(current, prev):
            state["net_creation_1d_cny"] = sum(
                (current["shares"][c] - prev["shares"][c]) * current["nav"][c]["nav"] for c in CORE_FOUR
            )
            den = caps.get((dates[pos - 1], DENOM_KINDS[0]))
            if ord_row and den:
                old = prev["aum"] / den["value_cny"]
                state["coverage_change_1d"] = state["ordinary_float_coverage_ratio"] / old - 1
    if pos >= 5:
        initial = per_day(pos - 5)
        if initial:
            sum_flow = 0.0
            complete = True
            for j in range(pos - 4, pos + 1):
                cur, before = per_day(j), per_day(j - 1)
                if cur is None or before is None or action_suspected(cur, before):
                    complete = False
                    break
                sum_flow += sum((cur["shares"][c] - before["shares"][c]) * cur["nav"][c]["nav"]
                                for c in CORE_FOUR)
            if complete:
                state["net_creation_5d_cny"] = sum_flow
            den = caps.get((dates[pos - 5], DENOM_KINDS[0]))
            if ord_row and den:
                old = initial["aum"] / den["value_cny"]
                state["coverage_change_5d"] = state["ordinary_float_coverage_ratio"] / old - 1
    if pos + 1 < len(dates) and pos >= 5:
        disclosure_cutoff = datetime.fromisoformat(dates[pos + 1] + "T15:00:00+08:00")
        rows_needed = [caps.get((dates[j], DENOM_KINDS[0])) for j in (pos, pos - 1, pos - 5)]
        state["denominator_known_by_t_plus_1"] = bool(
            all(row and _timestamp(row["published_at"], "denominator") <= disclosure_cutoff
                for row in rows_needed)
        )
        nav_stamps = (nav[dates[j]][c].get("published_at")
                      for j in (pos, pos - 1, pos - 5) for c in CORE_FOUR
                      if dates[j] in nav and c in nav[dates[j]])
        state["nav_not_known_late_by_t_plus_1"] = all(
            not stamp or _timestamp(stamp, "NAV") <= disclosure_cutoff
            for stamp in nav_stamps
        )
    # Historical cache has no first-public-time series for ETF shares. A stamped
    # NAV/denominator alone cannot retroactively establish when the signal was known.
    state["ratio_pit_verified"] = False
    return state


def _rows(prices, shares, nav, caps):
    """Use the exact index trading calendar for both lookbacks and forward exits."""
    dates = sorted(prices)
    rows = []
    for i, day in enumerate(dates):
        p = prices[day]
        ret5 = p / prices[dates[i - 5]] - 1 if i >= 5 else None
        draw20 = p / max(prices[d] for d in dates[i - 19:i + 1]) - 1 if i >= 19 else None
        down = i >= 19 and (ret5 < 0 or draw20 <= -0.05)
        # Strict all-four continuity across the lookback: never carry values over
        # an exchange holiday or missing daily ETF snapshot.
        share1 = share5 = None
        if i >= 5 and all(d in shares and all(c in shares[d] for c in CORE_FOUR)
                          for d in (day, dates[i - 1], dates[i - 5])):
            s0 = sum(shares[day].values())
            share1 = s0 / sum(shares[dates[i - 1]].values()) - 1
            share5 = s0 / sum(shares[dates[i - 5]].values()) - 1
        detail = _ratio_and_flow(day, dates, i, shares, nav, caps)
        ratio1, ratio5 = detail["coverage_change_1d"], detail["coverage_change_5d"]
        flow1, flow5 = detail["net_creation_1d_cny"], detail["net_creation_5d_cny"]
        control_signal = bool(down and share1 is not None and share5 is not None)
        share_signal = bool(control_signal and share1 > 0 and share5 > 0)
        ratio_signal = bool(down and ratio1 is not None and ratio5 is not None
                            and flow1 is not None and flow5 is not None
                            and ratio1 > 0 and ratio5 > 0 and flow1 > 0 and flow5 > 0
                            and detail["denominator_known_by_t_plus_1"]
                            and detail["nav_not_known_late_by_t_plus_1"])
        rows.append({"date": day, "index_close": p, "index_ret5": ret5,
                     "index_draw20": draw20, "market_down": down,
                     "shares_growth_1d": share1, "shares_growth_5d": share5,
                     "downturn_control_event": control_signal,
                     "share_proxy_event": share_signal,
                     "coverage_primary_event": ratio_signal, **detail})
    return rows


def _wilson(wins, n):
    if not n:
        return None
    z = 1.96
    a = wins / n
    center = (a + z * z / (2 * n)) / (1 + z * z / n)
    radius = z * math.sqrt((a * (1 - a) + z * z / (4 * n)) / n) / (1 + z * z / n)
    return [round(max(0, center - radius), 6), round(min(1, center + radius), 6)]


def _events(rows, key, *, cooldown=10):
    positions = [i for i, row in enumerate(rows) if row[key]]
    events = []
    last = -10_000
    for i in positions:
        if i - last <= cooldown:
            continue
        last = i
        exits = {}
        for horizon in HORIZONS:
            end = i + 2 + horizon
            if end >= len(rows):
                exits[str(horizon)] = None
            else:
                entry = rows[i + 2]["index_close"]
                exit_ = rows[end]["index_close"]
                ret = exit_ / entry - 1
                exits[str(horizon)] = {"exit_date": rows[end]["date"],
                                        "index_return": round(ret, 9),
                                        "up": ret > 0}
        events.append({
            "id": f"{key}:{rows[i]['date']}",
            "signal_date": rows[i]["date"],
            "decision_date": rows[i + 1]["date"] if i + 1 < len(rows) else None,
            "entry_date": rows[i + 2]["date"] if i + 2 < len(rows) else None,
            "signal_status": "RETROSPECTIVE_PIT_UNVERIFIED" if key != "market_down"
                             else "INDEX_DOWNTURN_CONTROL",
            "outcomes": exits,
        })
    return {"raw_signal_days": len(positions), "events": events}


def _stats(bag):
    output = {"raw_signal_days": bag["raw_signal_days"],
              "event_clusters": len(bag["events"]), "horizons": {}, "by_year": {}}
    for horizon in HORIZONS:
        k = str(horizon)
        matured = [e for e in bag["events"] if e["outcomes"][k] is not None]
        wins = sum(e["outcomes"][k]["up"] for e in matured)
        output["horizons"][k] = {
            "matured_events": len(matured), "wins": wins,
            "hit_rate": round(wins / len(matured), 6) if matured else None,
            "wilson95": _wilson(wins, len(matured)),
            "mean_index_return": (round(sum(e["outcomes"][k]["index_return"] for e in matured)
                                        / len(matured), 8) if matured else None),
        }
    for year in sorted({e["signal_date"][:4] for e in bag["events"]}):
        selection = [e for e in bag["events"] if e["signal_date"].startswith(year)]
        output["by_year"][year] = {str(h): {
            "matured": sum(e["outcomes"][str(h)] is not None for e in selection),
            "wins": sum(e["outcomes"][str(h)] is not None and e["outcomes"][str(h)]["up"]
                        for e in selection),
        } for h in HORIZONS}
    return output


def replay(prices, shares, *, nav=None, denominators=None, source_provenance=None):
    nav, denominators = nav or {}, denominators or {}
    rows = _rows(prices, shares, nav, denominators)
    groups = {kind: _events(rows, key)
              for kind, key in (("coverage_primary", "coverage_primary_event"),
                                ("share_proxy", "share_proxy_event"),
                                ("downturn_control", "downturn_control_event"))}
    return {
        "version": VERSION,
        "experiment_id": "EXP-0010",
        "trade_authorized": False,
        "actor_attribution": "UNVERIFIED_ETF_WIDE_FLOW_NOT_NATIONAL_TEAM_ACCOUNT",
        "source_provenance": source_provenance or {},
        "method": {
            "codes": list(CORE_FOUR),
            "primary": "sum(shares*same_day_NAV)/CSI300_ordinary_float_mv",
            "secondary": "sum(shares*same_day_NAV)/CSI300_free_float_mv",
            "event": "market_down AND coverage_change_1d>0 AND coverage_change_5d>0 "
                     "AND NAV_weighted_flow_1d>0 AND NAV_weighted_flow_5d>0",
            "market_down": "CSI300_close_5d<0 OR 20d_peak_drawdown<=-5pct",
            "entry": "signal_t then T+1 disclosure assumption, T+2 close index proxy",
            "exit": "T+2+h close for h=5,10,20 sessions",
            "cooldown_sessions": 10,
            "coverage_pit_warning": "Historical NAV and ETF share-cache publication time not independently verified",
            "baseline_warning": "same four-share complete-date universe; separately clustered, not paired causal lift",
        },
        "data_quality": {
            "first_index_day": rows[0]["date"] if rows else None,
            "last_index_day": rows[-1]["date"] if rows else None,
            "first_full_four_share_day": min(shares) if shares else None,
            "last_full_four_share_day": max(shares) if shares else None,
            "index_sessions": len(rows),
            "four_share_days": len(shares),
            "ratio_days": sum(x["ordinary_float_coverage_ratio"] is not None for x in rows),
            "ratio_pit_verified_days": 0,
            "missing_nav_index_sessions": sum(x["ratio_status"] == "NAV_MISSING" for x in rows),
            "missing_denom_with_nav_sessions": sum(x["ratio_status"] == "DENOMINATOR_MISSING"
                                                  for x in rows),
            "signal_days_by_status": dict(Counter("ratio_available" if x["ordinary_float_coverage_ratio"] is not None
                                                 else x["ratio_status"] for x in rows)),
        },
        "summary": {name: _stats(bag) for name, bag in groups.items()},
        "events": {name: bag["events"] for name, bag in groups.items()},
        "daily": [r for r in rows if r["date"] in shares and
                  (r["market_down"] or r["ordinary_float_coverage_ratio"] is not None)],
    }


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
