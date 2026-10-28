# A-share momentum runner | 中国A股三日追涨研究引擎

A **real GitHub Actions-powered** research prototype with fail-closed controls. Uses actual third-party market data; never places broker orders.

## Verified execution (2026-10-28)
- ✅ GitHub App authorized; connector commits succeeded.
- ✅ Actions installation and deterministic tests succeeded.
- ✅ Real historical data fetched and validated for 12 fixed watchlist stocks (not a comprehensive market screen).
- ✅ AKQuant API smoke ran; this **is NOT the three-day strategy's engine**.
- ✅ Custom three-day OHLC exploratory replay ran on 45 trades and QuantStats run completed in [successful action 40681563446](../../actions/runs/40681563446).
- ⚠️ This preliminary, **biased** research sample: 42.22% profitable, -0.277% mean per trade after approximate costs. There is no out-of-sample validation or true intraday T+3 14:50 executable-price modeling.
- ⚠️ Current implementation uses a **fixed 12-stock fallback watchlist** when full-market snapshot fails; it is not whole-market selection.
- ⚠️ GitHub Actions schedule can start late; intraday quotes are NOT reliably validated and there is no persistent actual-trade ledger yet.

**Hard gate:** In the current research-only version, `signals.json` must never contain actionable buy orders. `research_candidates` are not validated trading recommendations.

## Running
Actions: [workflow page](../../actions/workflows/ashare.yml).
Cron (UTC): 00:30, 04:30, 09:30 on weekdays (Beijing 08:30/12:30/17:30). Actual China exchange holidays are checked in Python.

Local: `python -m pip install -r requirements.txt && python -m pytest -q && python runner.py --phase close --out output`

Output artifacts:
- `audit.json`: dependencies, providers, timestamps, failure reasons, replay metadata.
- `signals.json`: real-data research candidates only, with explicitly unverified intraday conditions.
- `historical_trades_exploratory.json`: illustrative daily OHLC trade replay with assumptions.

## Source and validation
- [AKShare](https://github.com/akfamily/akshare) — market data APIs.
- [AKQuant](https://github.com/akfamily/akquant) — engine smoke test; full strategy port not yet integrated.
- [QuantStats](https://github.com/ranaroussi/quantstats) — trade-sequence stats (not actual portfolio drawdown).
- BaoStock — independent fallback to live historical series, provider clearly labeled.

All trade calculations require timestamped, authentic data; unit tests and successful dependency installation are necessary but insufficient. There is no automatic order placement.

## Reusable GitHub skill
[skills/github-connector-write-deploy/SKILL.md](skills/github-connector-write-deploy/SKILL.md) describes verified connector permissions, create/update file, GitHub Actions deployment and artifact audit, reusable in other projects.
