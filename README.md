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
- ✅ GitHub Actions now commits individual run records and the full observed research replay under [records/](records/); records include code SHA, input hashes and frozen signal IDs. This is **research execution evidence**, not proof of real orders. The earliest persisted full replay is [2026-10-28 close run 40683070796](records/2026-10-28/close/40683070796-a1.json).
- ✅ Added a chronological six-month holdout *diagnostic* with a 10-calendar-day embargo, plus separate T+3 locked-limit-down censoring and no fake reentry.
- ⚠️ Backtest is not independent OOS: the 12 currently-surviving symbols are a fixed, ex-post universe; daily OHLC cannot verify 14:50 execution.
- ⚠️ Real market breadth, financing/margin series and four ETF share/NAV freshness checks are not yet validated. Absent data are recorded as FAILED/NOT_FETCHED, not invented.
- ⚠️ GitHub Actions scheduled runs can start late; there is no true intraday signal activation or **actual customer trading ledger**. No broker orders are placed.

**Hard gate:** In the current research-only version, `signals.json` must never contain actionable buy orders. `research_candidates` are not validated trading recommendations.
 
### Validated research-only run (2026-10-28)
- [Run 40683516634](https://github.com/lican1213/a-share-momentum-runner/actions/runs/40683516634) passed **12 deterministic unit tests** and executed real 12-symbol data downloads, 45 daily-bar historical replay trades, and immutable-by-filename Git evidence.
- Across those 12 *ex-post selected* names, historical funnel recorded **110 possible signals**: 62 conditional price triggers, 44 no trigger, 4 gaps above chase ceiling; these are not independent executable portfolio trades.
- Of 45 completed OHLC-proxy trades, 42.22% show positive net return and mean net return is **-0.2769%**; in the most recent six-calendar-month historical partition (12 trades), win rate is **33.33%** and mean trade net return **-0.79889%**.
- These are diagnostic figures from a biased research subset, not future predictions, validated OOS, or a backtest suitable for deploying capital. The current model remains **trade authorization OFF**. 


## Running
Actions: [workflow page](../../actions/workflows/ashare.yml).
Cron (UTC): 00:30, 04:30, 09:30 on weekdays (Beijing 08:30/12:30/17:30). Actual China exchange holidays are checked in Python.

Local: `python -m pip install -r requirements.txt && python -m pytest -q && python runner.py --phase close --out output`

Output artifacts:
- `audit.json`: dependencies, providers, timestamps, failure reasons, replay metadata.
- `signals.json`: real-data research candidates only, with explicitly unverified intraday conditions.
- `historical_trades_exploratory.json`: daily OHLC trade replay with explicit execution proxies.\n- `records/YYYY-MM-DD/{pre,mid,close}/{run_id}-a{attempt}.json`: versioned by unique run id, includes audit, research signals, full trade replay and SHA256 hashes; retained in Git history. Git administrators could rewrite history, so not absolute immutability.

## Source and validation
- [AKShare](https://github.com/akfamily/akshare) — market data APIs.
- [AKQuant](https://github.com/akfamily/akquant) — engine smoke test; full strategy port not yet integrated.
- [QuantStats](https://github.com/ranaroussi/quantstats) — trade-sequence stats (not actual portfolio drawdown).
- BaoStock — independent fallback to live historical series, provider clearly labeled.

All trade calculations require timestamped, authentic data; unit tests and successful dependency installation are necessary but insufficient. There is no automatic order placement.

## Reusable GitHub skill
[skills/github-connector-write-deploy/SKILL.md](skills/github-connector-write-deploy/SKILL.md) describes verified connector permissions, create/update file, GitHub Actions deployment and artifact audit, reusable in other projects.
