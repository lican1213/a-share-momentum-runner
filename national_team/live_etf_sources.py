"""Collect ACTUAL exchange ETF total shares, and published NAV where available.

AKShare SSE fund_etf_scale_sse ALREADY converts official '10,000 shares'
to raw shares (*10000); SZSE fund_scale_daily_szse is already raw shares.
Never apply *10000 to AKShare SSE output again.

Capture time is an upper bound on first public availability: never claim a
historical trade signal was known earlier than its first archived observation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

CORE_FOUR = ("510300", "510310", "510330", "159919")
SSE_CODES = set(CORE_FOUR[:3])
SZSE_CODES = {"159919"}
SSE_URL = "https://www.sse.com.cn/assortment/fund/etf/list/scale/"
SZSE_URL = "https://www.szse.cn/market/fund/volume/etf/index.html"
NAV_URL = "https://fundf10.eastmoney.com/jjjz_{code}.html"


def as_canonical_shares(value: object, source: str) -> str:
    """Both supported AKShare provider outputs are already in SHARES."""
    if source not in {"akshare.sse.normalized_shares", "akshare.szse.raw_shares"}:
        raise ValueError("unsupported source/unit; check upstream interface implementation")
    try:
        n = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("missing invalid share value") from None
    if not n.is_finite() or n < 0:
        raise ValueError("nonfinite/negative ETF shares")
    return format(n, "f")


def normalized_day(frame, target: str, codes: set[str], source: str) -> dict:
    required = {"基金代码", "基金份额"}
    if not required.issubset(frame.columns):
        raise ValueError(f"{source}: missing code/share fields")
    column = "统计日期" if source.startswith("akshare.sse") else "日期"
    if column not in frame.columns:
        raise ValueError(f"{source}: date column missing")
    records: dict[str, str] = {}
    for _, row in frame.iterrows():
        code = str(row["基金代码"]).split(".")[0].zfill(6)
        if code not in codes:
            continue
        obs_day = str(row[column])[:10]
        if obs_day != target:
            continue
        if code in records:
            raise ValueError(f"{source}: duplicate {code} {target}")
        records[code] = as_canonical_shares(row["基金份额"], source)
    return records


def history_nav(frame, code: str, dates: set[str]) -> dict[str, str]:
    if not {"净值日期", "单位净值"}.issubset(frame.columns):
        raise ValueError(f"{code}: invalid ETF NAV source schema")
    out = {}
    for _, row in frame.iterrows():
        d = str(row["净值日期"])[:10]
        if d not in dates:
            continue
        if d in out:
            raise ValueError(f"{code}: duplicate NAV date {d}")
        raw = str(row["单位净值"])
        try:
            n = Decimal(raw)
        except InvalidOperation:
            raise ValueError(f"{code}: invalid NAV {d}")
        if not n.is_finite() or n <= 0:
            raise ValueError(f"{code}: nonpositive NAV {d}")
        out[d] = format(n, "f")
    return out


def collect(ak, asof: date, run_id: str, attempt: str, out_root: Path):
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    if asof > now.date():
        raise ValueError("no future date observations")
    dates = [(asof - timedelta(days=n)).isoformat() for n in range(21)]
    dates.reverse()
    # Retrieval of past dates TODAY does not establish that those dates'
    # values were available to someone at that historical time.
    result = {
        "schema": 1, "status": "ATTEMPTED_NO_COMPLETE_FACTOR",
        "run_id": run_id, "run_attempt": attempt,
        "capture_time_beijing": now.isoformat(),
        "first_observed_no_earlier_than": now.isoformat(),
        "asof_requested": asof.isoformat(),
        "core_codes": list(CORE_FOUR),
        "unit": "raw_shares",
        "sources": {
            "SSE": {"url": SSE_URL, "api": "akshare.fund_etf_scale_sse",
                    "normalization": "AKShare already *10000 from official 10,000-share display"},
            "SZSE": {"url": SZSE_URL, "api": "akshare.fund_scale_daily_szse",
                     "normalization": "AKShare output already raw shares"},
            "NAV": {"url_template": NAV_URL,
                    "api": "akshare.fund_etf_fund_info_em",
                    "normalization": "CNY per fund share; may be unavailable"},
        },
        "observations_by_date": {}, "raw_input_hashes": {}, "errors": [],
        "availability_status": "historical data first captured NOW, not earlier public event timestamps",
        "investor_identity": "UNATTRIBUTED_TO_HUIJIN_OR_ANY_OTHER_ENTITY",
        "trade_signal_authorized": False,
    }
    start = (asof - timedelta(days=21)).strftime("%Y%m%d")
    end = asof.strftime("%Y%m%d")
    try:
        df = ak.fund_scale_daily_szse(start_date=start, end_date=end, symbol="ETF")
        result["raw_input_hashes"]["SZSE"] = hashlib.sha256(df.to_csv(index=False).encode()).hexdigest()
        for day in dates:
            rows = normalized_day(df, day, SZSE_CODES, "akshare.szse.raw_shares")
            if rows:
                result["observations_by_date"].setdefault(day, {}).update(
                    {k: {"shares": v, "shares_source": "SZSE"} for k,v in rows.items()})
    except Exception as exc:
        result["errors"].append(f"SZSE_DAILY:{type(exc).__name__}:{str(exc)[:220]}")
        # SZSE separate FUND LIST API supplies a latest snapshot, but NO
        # declared observation trading date. Preserve it as UNDATED only;
        # never silently backdate to the requested trading session.
        try:
            latest = ak.fund_etf_scale_szse()
            subset = latest[latest["基金代码"].astype(str).str.zfill(6).eq("159919")]
            if len(subset) != 1:
                raise ValueError(f"expected one 159919 row, found {len(subset)}")
            share = as_canonical_shares(subset.iloc[0]["基金份额"], "akshare.szse.raw_shares")
            result["latest_undated_szse_snapshot"] = {
                "fund_code": "159919", "shares": share,
                "first_observed_at": now.isoformat(),
                "observation_exchange_trading_date": None,
                "cannot_calculate_daily_share_change": True,
                "url": "https://fund.szse.cn/marketdata/fundslist/index.html",
                "api": "akshare.fund_etf_scale_szse",
            }
            result["raw_input_hashes"]["SZSE_LATEST_UNDATED"] = hashlib.sha256(
                latest.to_csv(index=False).encode()).hexdigest()
        except Exception as alt:
            result["errors"].append(f"SZSE_LATEST_UNDATED:{type(alt).__name__}:{str(alt)[:220]}")
    # Independent official dated JSON fallback. The per-fund endpoint uses
    # 10,000-share units, unlike AKShare's already-normalized SSE/whole-SZSE.
    # No fabricated disclosure timestamp: first known publication is capture.
    sz_dates = [d for d,r in result["observations_by_date"].items() if "159919" in r]
    if not sz_dates:
        try:
            from national_team.szse_json import fetch_one_szse_fund, LANDING
            dated = fetch_one_szse_fund("159919",(asof-timedelta(days=21)).isoformat(),
                                        asof.isoformat())
            for day, shares in dated.items():
                result["observations_by_date"].setdefault(day,{})["159919"] = {
                    "shares":shares,"shares_source":"SZSE_DATED_JSON",
                    "shares_source_url":LANDING,
                    "first_observed_at":datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
                }
            result["SZSE_DATED_JSON"]={"count":len(dated),"status":"OK" if dated else "EMPTY",
                                      "unit_conversion":"official current_size ten_thousand_shares x 10000"}
        except Exception as exc:
            result["errors"].append(f"SZSE_DATED_JSON:{type(exc).__name__}:{str(exc)[:240]}")
    # Bounded native SSE HTTPS adapter. Unlike AKShare's internal requests.get,
    # each attempt has an explicit timeout, and official TOT_VOL units (10k)
    # are multiplied exactly once into raw shares.
    from national_team.sse_direct import fetch_sse_direct
    try:
        from national_team.event_pipeline import exchange_sessions
        sse_days=set(exchange_sessions(asof.isoformat(),lookback_days=15))
    except Exception as exc:
        result["errors"].append(f"SSE_CALENDAR:{type(exc).__name__}:{str(exc)[:130]}")
        sse_days={d for d in dates[-15:] if date.fromisoformat(d).weekday()<5}
    for day in [d for d in dates[-15:] if d in sse_days]:
        try:
            rows = fetch_sse_direct(day,attempts=2,timeout=10)
            result["raw_input_hashes"][f"SSE_DIRECT:{day}"] = hashlib.sha256(
                json.dumps(rows,sort_keys=True).encode()).hexdigest()
            if rows:
                result["observations_by_date"].setdefault(day, {}).update(
                    {k: {"shares": v, "shares_source": "SSE_DIRECT",
                         "shares_source_url":SSE_URL} for k,v in rows.items()})
        except Exception as exc:
            result["errors"].append(f"SSE_DIRECT:{day}:{type(exc).__name__}:{str(exc)[:165]}")
    candidates = {day for day in result["observations_by_date"] if day <= asof.isoformat()}
    for code in CORE_FOUR:
        try:
            frame = ak.fund_etf_fund_info_em(fund=code, start_date=start, end_date=end)
            result["raw_input_hashes"][f"NAV:{code}"] = hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()
            nav_rows = history_nav(frame, code, candidates)
            for day, nav in nav_rows.items():
                if code in result["observations_by_date"][day]:
                    result["observations_by_date"][day][code]["nav"] = nav
                    result["observations_by_date"][day][code]["nav_source"] = "fund_etf_fund_info_em: Eastmoney"
        except Exception as exc:
            result["errors"].append(f"NAV:{code}:{type(exc).__name__}:{str(exc)[:200]}")

    # Partial descriptive facts must be preserved without silently claiming
    # they are the ORIGINAL complete four-ETF signal.
    three_sse = {"510300", "510310", "510330"}
    sse_complete = sorted(d for d, funds in result["observations_by_date"].items()
                          if three_sse.issubset(funds)
                          and all("nav" in funds[c] for c in three_sse))
    if len(sse_complete) >= 2:
        prev_day, last_day = sse_complete[-2:]
        current = result["observations_by_date"][last_day]
        previous = result["observations_by_date"][prev_day]
        contribution = {code: (
            Decimal(current[code]["shares"]) - Decimal(previous[code]["shares"])
        ) * Decimal(current[code]["nav"]) for code in sorted(three_sse)}
        result["partial_SSE_three_only"] = {
            "label": "SSE three ETF flow only, EXCLUDES Shenzhen 159919",
            "period": [prev_day,last_day],
            "same_day_NAV_weighted_flow_cny": format(sum(contribution.values(),Decimal(0)),"f"),
            "per_etf_flow_cny": {c: format(v,"f") for c,v in contribution.items()},
            "consecutive_exchange_sessions_verified": False,
            "not_full_original_four_factor": True,
            "not_proof_of_huijin_orders": True,
        }
    # Earliest observable public availability is conservatively when THIS
    # run has finished collecting, not when the job started.
    result["capture_completed_beijing"] = datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    result["first_observed_no_earlier_than"] = result["capture_completed_beijing"]
    complete_shares = sorted(d for d, fund in result["observations_by_date"].items()
                             if set(CORE_FOUR).issubset(fund))
    complete_nav = sorted(d for d in complete_shares if all(
        "nav" in result["observations_by_date"][d][code] for code in CORE_FOUR))
    result["dates_with_four_shares"] = complete_shares
    result["dates_with_four_shares_and_nav"] = complete_nav
    if not complete_shares and "partial_SSE_three_only" in result:
        result["status"] = "PARTIAL_SSE_THREE_WITH_NAV_ONLY"
    if complete_shares:
        last = complete_shares[-1]
        result["latest_complete_shares_date"] = last
        idx = complete_shares.index(last)
        if idx:
            prev = complete_shares[idx-1]
            # Delta is valid only if immediately previous exchange trading day;
            # with exchange calendar unavailable label adjacent observation,
            # not automatically consecutive MARKET sessions.
            result["last_two_complete_observation_dates"] = [prev,last]
            result["last_pair_share_changes"] = {
                code: format(Decimal(result["observations_by_date"][last][code]["shares"]) -
                             Decimal(result["observations_by_date"][prev][code]["shares"]), "f")
                for code in CORE_FOUR
            }
            result["last_pair_trading_day_consecutiveness_verified"] = False
        result["status"] = "SHARES_OBSERVED_NO_VERIFIED_TRADE_SIGNAL"
    if len(complete_nav) >= 6:
        result["status"] = "SHARES_NAV_HISTORY_OBSERVED_NOT_PIT_HISTORICAL_SIGNALS"
        result["factor_arithmetic_possible"] = True
    else:
        result["factor_arithmetic_possible"] = False
    # Source timestamps and complete XSHG trading-session adjacency are
    # explicitly reconciled after the real provider observations are collected.
    try:
        from national_team.event_pipeline import exchange_sessions, reconcile_funding_snapshot
        sessions=exchange_sessions(asof.isoformat(),lookback_days=21)
        result["funding_event"]=reconcile_funding_snapshot(result,sessions)
        if result["funding_event"]["four_etf_factor"] is not None:
            result["status"]=(
                "PRIOR_FULL_FOUR_AND_LATEST_PARTIAL_OBSERVED"
                if result["funding_event"]["status"]=="PARTIAL_LATEST_WITH_PRIOR_FULL_FOUR_FACTOR"
                else "FOUR_ETF_FACTOR_OBSERVED_AFTER_CAPTURE_NOT_HISTORICAL_PIT"
            )
            result["factor_arithmetic_possible"]=True
    except Exception as exc:
        result["errors"].append(f"CALENDAR_OR_EVENT:{type(exc).__name__}:{str(exc)[:230]}")
        result["funding_event"]={"status":"UNVERIFIED_CALENDAR_OR_FACTOR"}
    folder = out_root / asof.isoformat()
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{run_id}-a{attempt}.json"
    target = folder / filename
    if target.exists():
        raise FileExistsError(f"do not overwrite existing evidence: {target}")
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    return target, result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--asof", default=datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat())
    parser.add_argument("--out", default="records/national_team_etf")
    args = parser.parse_args()
    import akshare as ak
    result_path, result = collect(ak, date.fromisoformat(args.asof),
                                   os.environ.get("GITHUB_RUN_ID", "local"),
                                   os.environ.get("GITHUB_RUN_ATTEMPT", "1"), Path(args.out))
    print(json.dumps({"status": result["status"],
                      "complete_shares_days": len(result["dates_with_four_shares"]),
                      "complete_nav_days": len(result["dates_with_four_shares_and_nav"]),
                      "error_count": len(result["errors"]),
                      "record": str(result_path)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
