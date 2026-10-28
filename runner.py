"""A-share scheduled research runner. Fails closed; never places brokerage orders.

External prices: AKShare historical day bars (raw unadjusted) and snapshot;
AKQuant is separately exercised as a library smoke test, not misrepresented
as the execution model for the custom daily-bar three-day replay.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata as md
import json
import logging
import re
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import akshare as ak
import pandas as pd
import quantstats as qs

from strategy import candidate_at, historical_trades, normalize


TZ = ZoneInfo("Asia/Shanghai")
ALLOWED = re.compile(r"^(000|001|002|003|600|601|603|605)[0-9]{3}$")
PHASES = {"pre": (8, 30), "mid": (12, 30), "close": (17, 30)}
MAX_UNIVERSE = 15
logger = logging.getLogger("runner")


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def versions() -> dict:
    out = {"python": sys.version.split()[0]}
    for item in ("akshare", "akquant", "quantstats", "pandas"):
        try:
            out[item] = md.version(item)
        except md.PackageNotFoundError:
            out[item] = "MISSING"
    return out


def trade_days(now: datetime) -> tuple[list, str]:
    """Primary: live Sina trade-date feed; backup: exchange_calendars XSHG."""
    try:
        df = ak.tool_trade_date_hist_sina()
        if "trade_date" not in df.columns or df.empty:
            raise ValueError("Sina trade calendar missing trade_date")
        days = sorted(set(pd.to_datetime(df["trade_date"]).dt.date))
        if len(days) < 100 or days[-1] < now.date():
            raise ValueError("Sina calendar stale or incomplete")
        return days, "AKShare Sina live holiday calendar"
    except Exception as exc:
        logger.warning("Sina calendar unavailable: %r; trying exchange_calendars XSHG", exc)
        import exchange_calendars as xcals
        cal = xcals.get_calendar("XSHG")
        start = pd.Timestamp(now.date() - timedelta(days=360))
        end = pd.Timestamp(now.date() + timedelta(days=15))
        days = [x.date() for x in cal.sessions_in_range(start, end)]
        if len(days) < 100 or days[-1] < now.date():
            raise RuntimeError("backup XSHG calendar incomplete; stop, no signal")
        return days, "exchange_calendars XSHG third-party fallback; verify against SSE notices"


def fetch_universe(asof: datetime) -> list[dict]:
    # Snapshot lacks per-row exchange timestamp. Only used for WATCHLIST
    # liquidity/universe filtering, never a claimed up-to-second trade price.
    df = ak.stock_zh_a_spot_em()
    fields = ["代码", "名称", "成交额", "最新价", "涨跌幅"]
    if any(x not in df.columns for x in fields):
        raise ValueError(f"snapshot schema drift: {list(df.columns)[:20]}")
    df = df[fields].copy()
    df["代码"] = df["代码"].astype(str).str.zfill(6)
    df["名称"] = df["名称"].astype(str)
    df = df[df["代码"].map(lambda x: bool(ALLOWED.fullmatch(x)))]
    df = df[~df["名称"].str.contains("ST|退|\\*", case=False, regex=True)]
    for c in ["成交额", "最新价", "涨跌幅"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["成交额", "最新价", "涨跌幅"])
    df = df[(df["成交额"] > 1e8) & (df["最新价"] > 1)]
    # Strong turnover with limited single-day chase. Pre-market values may
    # represent prior session; no intraday implication is inferred.
    df = df[(df["涨跌幅"] > 0.3) & (df["涨跌幅"] < 8.5)]
    df = df.sort_values("成交额", ascending=False).head(MAX_UNIVERSE)
    if df.empty:
        raise ValueError("empty executable-market watchlist after filters")
    return [{"symbol": r["代码"], "name": r["名称"], "snapshot_price_unverified": float(r["最新价"]),
             "snapshot_capture": asof.isoformat()} for _, r in df.iterrows()]


def akquant_smoke_test(df: pd.DataFrame, symbol: str) -> dict:
    """Actually calls AKQuant on genuine day bars, but this is only an API smoke test."""
    import akquant as aq
    from akquant import Strategy

    class EngineSmokeStrategy(Strategy):
        def on_bar(self, bar):
            # Minimal smoke: intentionally NOT the 3-day momentum strategy.
            pos = self.get_position(bar.symbol)
            if pos == 0 and bar.close > bar.open:
                self.buy(symbol=bar.symbol, quantity=100)
            elif pos > 0 and bar.close < bar.open:
                self.close_position(symbol=bar.symbol)

    code = ("sh" if symbol.startswith("6") else "sz") + symbol
    bars = df[["date", "open", "high", "low", "close", "volume"]].copy()
    result = aq.run_backtest(data=bars, strategy=EngineSmokeStrategy, initial_cash=100000.0, symbols=code)
    return {"status": "success", "engine": "AKQuant", "test": "simple-candle API smoke only",
            "is_3day_strategy_backtest": False, "result_excerpt": str(result)[:500]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=PHASES, required=True)
    parser.add_argument("--out", type=Path, default=Path("output"))
    args = parser.parse_args()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    now = datetime.now(TZ)
    audit = {
        "started_at": now.isoformat(), "phase": args.phase, "timezone": str(TZ),
        "implementation": "daily-bar research runner v0.1",
        "dependencies": versions(), "status": "STARTED",
        "limitations": [
            "AKShare snapshot has no verified per-row exchange timestamp",
            "daily OHLC can only approximate T+3 close, not 14:50 executable price",
            "selected current watchlist produces survivorship-biased replay",
            "historical OHLC cannot resolve every intraday order-fill sequence",
            "not a whole-A-share backtest; no brokerage trades or actual portfolio",
        ],
    }
    write_json(out / "audit.json", audit)
    try:
        days, calendar_source = trade_days(now)
        audit["calendar_source"] = calendar_source
        today = now.date()
        if today not in days:
            audit.update(status="MARKET_CLOSED", reason="not in verified trading-day list",
                         calendar_last=str(days[-1]))
            write_json(out / "audit.json", audit)
            return 0
        past = [d for d in days if d < today]
        expected = today if args.phase == "close" else past[-1]
        audit["required_history_date"] = str(expected)
        if args.phase == "close" and now.hour < 16:
            raise ValueError("close phase before verified EOD publication window")
        universe = fetch_universe(now)
        audit["universe_size"] = len(universe)
        audit["universe_method"] = "top turnover non-ST main-board from AKShare snapshot"
        audit["data_providers"] = ["AKShare stock_zh_a_spot_em (Eastmoney)",
                                  "AKShare stock_zh_a_hist (Eastmoney)",
                                  "AKShare tool_trade_date_hist_sina (Sina)"]
        audit["universe_snapshot_note"] = "capture time is fetch time, not exchange quote time"
        candidates, all_trades, verified = [], [], []
        problems = []
        raw_hashes = {}
        start_date = (now.date() - timedelta(days=920)).strftime("%Y%m%d")
        end_date = (now.date() + timedelta(days=1)).strftime("%Y%m%d")
        clean_first = None
        for item in universe:
            sym = item["symbol"]
            try:
                raw = ak.stock_zh_a_hist(symbol=sym, period="daily", start_date=start_date,
                                         end_date=end_date, adjust="")
                if raw is None or raw.empty:
                    raise ValueError("empty history")
                raw_hashes[sym] = hashlib.sha256(raw.to_csv(index=False).encode("utf-8")).hexdigest()
                bars = normalize(raw)
                latest = bars.iloc[-1]["date"].date()
                if latest != expected:
                    raise ValueError(f"history stale/future: {latest}, expected {expected}")
                verified.append({"symbol": sym, "name": item["name"],
                                 "last_bar_date": str(latest), "bar_count": len(bars)})
                if clean_first is None:
                    clean_first = (sym, bars)
                signal = candidate_at(bars, len(bars) - 1)
                if signal:
                    candidates.append({"symbol": sym, "name": item["name"], **signal})
                all_trades.extend(historical_trades(bars, sym))
            except Exception as exc:
                problems.append({"symbol": sym, "error": f"{type(exc).__name__}: {exc}"})
        audit.update(verified_symbols=len(verified), failed_symbols=problems,
                     snapshot_symbols=len(universe), sha256_histories=raw_hashes,
                     historical_replay_trades=len(all_trades))
        if len(verified) < 5:
            raise RuntimeError("fewer than five symbols pass live data quality and freshness gates")
        if clean_first is None:
            raise RuntimeError("no verified historical bars")
        try:
            audit["akquant_smoke"] = akquant_smoke_test(clean_first[1], clean_first[0])
        except Exception as exc:
            audit["akquant_smoke"] = {"status": "failed", "error": repr(exc),
                                   "is_3day_strategy_backtest": False}
        # The independent daily-bar replay is real code run on downloaded data,
        # not a claim that AKQuant ran the same strategy.
        all_trades.sort(key=lambda x: (x["entry_date"], x["symbol"]))
        write_json(out / "historical_trades_exploratory.json",
                   {"data": all_trades,
                    "warning": "CURRENT universe and daily T+3-close proxy; not unbiased OOS results"})
        candidates.sort(key=lambda x: (x["volume_multiple"], x["return5"]), reverse=True)
        # Signals reference last verified daily close, not a live intra-day fill.
        signals = candidates[:3]
        write_json(out / "signals.json", {
            "status": "computed_from_actual_daily_data",
            "asof": str(expected), "phase": args.phase,
            "signals": signals, "source": "AKShare Eastmoney unadjusted daily OHLC",
            "no_actual_fills": True, "intraday_activation_unknown": True})
        if all_trades:
            returns = pd.Series([float(x["net_return"]) for x in all_trades])
            audit["exploratory_history"] = {
                "trade_count": len(all_trades), "winning_fraction": round(float((returns > 0).mean()), 6),
                "mean_trade_return": round(float(returns.mean()), 6),
                "sample_type": "selected-current-universe, overlapping cross-sectional trades",
            }
            # QuantStats on a sequential hypothetical trade series, explicitly
            # not comparable to an actual calendar-day portfolio drawdown.
            # QuantStats max_drawdown expects RETURNS, not equity levels.
            audit["quantstats_trade_sequence_max_drawdown"] = float(qs.stats.max_drawdown(returns.reset_index(drop=True)))
            audit["quantstats_warning"] = "trade-sequence only, NOT actual portfolio max drawdown"
        audit["status"] = "COMPUTED_WITH_LIMITATIONS"
        audit["ended_at"] = datetime.now(TZ).isoformat()
        write_json(out / "audit.json", audit)
        print(json.dumps({"status": audit["status"], "verified": len(verified),
                          "signals": len(signals), "historical_trades": len(all_trades),
                          "akquant_smoke": audit["akquant_smoke"]["status"]}, ensure_ascii=False))
        # Strict user requirement: if AKQuant smoke failed do not treat the
        # full system as validated; artifacts still uploaded by Actions.
        return 0 if audit["akquant_smoke"]["status"] == "success" else 2
    except Exception as exc:
        audit.update(status="EXECUTION_FAILED", error=f"{type(exc).__name__}: {exc}",
                     traceback=traceback.format_exc(limit=8),
                     ended_at=datetime.now(TZ).isoformat(),
                     no_trading_signals_authorized=True)
        write_json(out / "audit.json", audit)
        print(audit["error"], file=sys.stderr)
        return 2


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    raise SystemExit(main())
