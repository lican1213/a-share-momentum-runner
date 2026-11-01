"""Append-only F1/F2 OHLC paper follow-up after the original frozen intent."""
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
from national_team.left_entry_outcomes import track

BJ = ZoneInfo("Asia/Shanghai")


def rows(frame):
    if "日期" in frame.columns:
        col = ("日期", "开盘", "最高", "最低", "收盘")
    else:
        col = ("date", "open", "high", "low", "close")
    if not all(x in frame.columns for x in col):
        raise ValueError("unknown OHLC schema")
    return [{"date": str(v[col[0]])[:10], "open": str(v[col[1]]),
             "high": str(v[col[2]]), "low": str(v[col[3]]), "close": str(v[col[4]])}
            for _, v in frame.iterrows()]


def collect(ak, freeze, asof):
    start = freeze["signal_session"]
    start_raw = (datetime.fromisoformat(start) + timedelta(days=1)).strftime("%Y%m%d")
    end = asof.replace("-", "")
    out = {"first_observed_at": None, "capture_time": None,
           "bars_by_symbol": {}, "source_sha256": {}, "source_url": {},
           "errors": {}}
    codes = ["510300"] + [o["stock"] for o in freeze["accounts"]["F1_LEFT"]["orders"]]
    for code in codes:
        try:
            if code == "510300":
                frame = ak.fund_etf_hist_em(symbol="510300", period="daily",
                                            start_date=start_raw, end_date=end, adjust="")
                url = "https://quote.eastmoney.com/sh510300.html"
            else:
                sym = ("sh" if code.startswith(("6", "9")) else "sz") + code
                frame = ak.stock_zh_a_daily(symbol=sym, start_date=start_raw,
                                            end_date=end, adjust="")
                url = "https://finance.sina.com.cn/realstock/company/"
            if frame is None or frame.empty:
                raise ValueError("no later daily market source")
            result = rows(frame)
            result = sorted((x for x in result if start < x["date"] <= asof),
                            key=lambda x: x["date"])
            if not result:
                raise ValueError("no future trading session observed")
            out["bars_by_symbol"][code] = result
            out["source_url"][code] = url
            out["source_sha256"][code] = hashlib.sha256(
                frame.to_csv(index=False).encode()).hexdigest()
        except Exception as exc:
            out["errors"][code] = f"{type(exc).__name__}:{str(exc)[:200]}"
    out["capture_time"] = datetime.now(BJ).isoformat()
    out["first_observed_at"] = out["capture_time"]
    return out


def latest_initial_freeze(root):
    files = sorted(Path(root).glob("*/*.json"))
    if not files:
        raise ValueError("V4 original freeze not yet published")
    acceptable = []
    for f in files:
        j = json.loads(f.read_text(encoding="utf-8"))
        if j.get("experiment_id") == "EXP-0011":
            acceptable.append((j["freeze_time"], str(f), j))
    if not acceptable:
        raise ValueError("no V4 frozen EXP-0011 record")
    acceptable.sort()
    return acceptable[0][1], acceptable[0][2]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--freeze-root", default="records/national_team_left_entry")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    freeze_path, frozen = latest_initial_freeze(args.freeze_root)
    now = datetime.now(BJ)
    import akshare as ak
    seen = collect(ak, frozen, now.date().isoformat())
    observed = datetime.now(BJ).isoformat()
    result = track(frozen, seen, observed_at=observed)
    result["freeze_path"] = freeze_path
    result["github_run_id"] = os.environ.get("GITHUB_RUN_ID")
    result["github_run_attempt"] = os.environ.get("GITHUB_RUN_ATTEMPT")
    result["github_source_commit"] = os.environ.get("GITHUB_SHA")
    out = Path(args.out)
    if out.exists():
        raise FileExistsError("refuse to overwrite follow-up evidence")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print(json.dumps({"asof": result["asof"],
                      "freeze_path": freeze_path,
                      "F1": [(x["stock"], x["status"]) for x in result["F1_LEFT"]],
                      "F2": [(x["stock"], x["status"]) for x in result["F2_WEAK"]],
                      "source_errors": result["errors"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
