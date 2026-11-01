"""EXP-0011 source-verified OHLC collection and immutable paper *intent* freeze."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from national_team.left_entry_v4 import freeze

BJ = ZoneInfo("Asia/Shanghai")


def next_weekday(d):
    """Only a planned session; exchange calendar must confirm the real first open."""
    day = d + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day.isoformat()


def _bars(frame):
    if "日期" in frame.columns:
        cols = ("日期", "开盘", "最高", "最低", "收盘")
    else:
        cols = ("date", "open", "high", "low", "close")
    if not all(c in frame.columns for c in cols):
        raise ValueError("unknown OHLC columns")
    rows = []
    for _, item in frame.iterrows():
        rows.append({"date": str(item[cols[0]])[:10], "open": str(item[cols[1]]),
                     "high": str(item[cols[2]]), "low": str(item[cols[3]]),
                     "close": str(item[cols[4]])})
    return rows


def collect(ak, watch, event_date, max_stocks=150):
    if not 1 <= max_stocks <= 200:
        raise ValueError("max stocks outside 1..200")
    pool = watch["candidate_pool_pre_filter"][:max_stocks]
    start = (datetime.fromisoformat(event_date) - timedelta(days=100)).strftime("%Y%m%d")
    end = event_date.replace("-", "")
    out = {"schema": 1, "asof": event_date, "universe": pool,
           "stocks": {}, "collection_errors": {}}
    for code in pool:
        for vendor in ("SINA", "EASTMONEY"):
            try:
                if vendor == "SINA":
                    sym = ("sh" if code.startswith(("6", "9")) else "sz") + code
                    frame = ak.stock_zh_a_daily(symbol=sym, start_date=start,
                                               end_date=end, adjust="")
                    url = "https://finance.sina.com.cn/realstock/company/"
                else:
                    frame = ak.stock_zh_a_hist(symbol=code, period="daily",
                                              start_date=start, end_date=end, adjust="")
                    url = "https://quote.eastmoney.com/"
                if frame is None or len(frame) < 21:
                    raise ValueError("stock OHLC unavailable or <21 sessions")
                bars = _bars(frame)
                bars = sorted((x for x in bars if x["date"] <= event_date),
                              key=lambda x: x["date"])[-45:]
                if len(bars) < 21 or bars[-1]["date"] != event_date:
                    raise ValueError("latest price session differs from funding day")
                out["stocks"][code] = {
                    "asof": event_date, "bars": bars, "vendor": vendor,
                    "source_url": url, "first_observed_at": datetime.now(BJ).isoformat(),
                    "source_sha256": hashlib.sha256(frame.to_csv(index=False).encode()).hexdigest()}
                break
            except Exception as exc:
                out["collection_errors"][f"{code}:{vendor}"] = (
                    f"{type(exc).__name__}:{str(exc)[:180]}")
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--v3", required=True)
    parser.add_argument("--watch", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--prices", help="fixture/persisted OHLC JSON; omit to fetch live AKShare")
    parser.add_argument("--max-stocks", type=int, default=150)
    args = parser.parse_args()
    v3 = json.loads(Path(args.v3).read_text(encoding="utf-8"))
    watch = json.loads(Path(args.watch).read_text(encoding="utf-8"))
    asof = v3["daily"][-1]["date"]
    if args.prices:
        prices = json.loads(Path(args.prices).read_text(encoding="utf-8"))
    else:
        import akshare as ak
        prices = collect(ak, watch, asof, max_stocks=args.max_stocks)
    now = datetime.now(BJ)
    result = freeze(v3, watch, prices, now=now.isoformat(),
                    next_session=next_weekday(now.date()))
    result["collection_errors"] = prices.get("collection_errors", {})
    result["collection_scope"] = {
        "completed_stock_source_count": len(prices.get("stocks", {})),
        "requested_source_count": len(prices.get("universe", [])),
        "session_note": "next_weekday is provisional; holiday and tradability rechecked at actual entry",
        "run_commit": os.environ.get("GITHUB_SHA"),
        "github_run_id": os.environ.get("GITHUB_RUN_ID"),
        "github_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT")}
    target = Path(args.out)
    if target.exists():
        raise FileExistsError("immutable evidence path exists")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",
                      encoding="utf-8")
    print(json.dumps({"status": result["accounts"]["F1_LEFT"]["state"],
                      "five_day_gate": result["admission"]["five_day_historical_directional_hit_rate"],
                      "eligible_stocks": result["universe"]["low_left_eligible"],
                      "source_stock_count": len(prices.get("stocks", {})),
                      "orders": [x["stock"] for x in result["accounts"]["F1_LEFT"]["orders"]],
                      "output": str(target)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
