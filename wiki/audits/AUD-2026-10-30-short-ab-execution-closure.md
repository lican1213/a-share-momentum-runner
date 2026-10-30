---
id: AUD-2026-10-30-short-ab-execution-closure
type: audit
status: pending-real-market-verification
created: 2026-10-30
updated: 2026-10-30
---
# A2/B short paper closure: execution and adversarial repair

A original, V2 frozen candidates and existing A2/B strategy parameters are unchanged. No backdated trade.

The ten original ranked securities now carry explicit daily filter results, rejection reasons and per-symbol vendor errors. An unverified candidate never counts as a verified rejection or licenses promotion of a lower-ranked candidate. Unaffected arms still generate independently verified paper candidates.

After prior freeze is demonstrably Git-archived before next 09:25, the first post-close scenario creates append-only entry and exit JSON events in records/national_team_short_ab/ledger/{entries,exits}/{A2,B}/. Entry terms, initial stop/target, benchmark and exit minute are not silently overwritten. Drift blocks synthetic profit.

Tests prove software behavior; G1 actual close freeze, G2 pre-open archived event, G3 completed minute replay and G4 cost-net outperformance remain separate verifications. No brokerage orders are enabled.

## 2026-10-30 additional adversarial repair

- Removed the synthetic +3% *pre-open* affordability rejection: valid low-gap 100-share orders are evaluated at next-session execution price, not eliminated using hypothetical highest permissible gap. Still rejects provably unaffordable lots and enforces the original entry-time max-position/max-risk limits.
- Prior **and** current ETF observations require timezone-aware per-field point-in-time stamps no later than the freeze; a future-stamped prior share/NAV is not allowed in the four-ETF daily difference.
- Both behaviors have counterexample-based automated tests.

## Independent 16:40 Beijing real-source readiness probe

A separate read-only workflow `national-team-short-probe.yml` probes the completed actual market session, all ten frozen V2 securities, the four-ETF archived event, and 510300/601825/600309 minute vendor reachability. The probe cannot call build_freeze, write a freeze path, generate a paper order, or increment paper positions. It saves `records/national_team_short_ab/probes/` with real run ID, SHA, provider errors and source hashes. This is a data-readiness check only, not G1/G2/G3 evidence.

## 2026-10-30 actual vendor failure and fallback repair

Real read-only source probe [41027686611](https://github.com/lican1213/a-share-momentum-runner/actions/runs/41027686611) at 16:37:58 Beijing obtained verified latest 2026-10-29 four-ETF net-creation proxy 8,742,148,830 CNY and 510300 close 4.065 on 2026-10-30, but **all ten stock OHLC sources** and sampled intraday bars failed Eastmoney push2 rate-limiting; generic A-share name lookup reset connection. These are actual failures, not strategy exclusions.

Remedy: query Shanghai Stock Exchange main-board names via `stock_info_sh_name_code` first, Sina unadjusted daily `stock_zh_a_daily` first for stocks, Eastmoney as secondary with per-process rate-limit circuit breaker. For 510300 ETF, prefer existing actual Eastmoney daily with Sina ETF fallback. For 1m exit/B2 evidence, Sina `stock_zh_a_minute` first, then Eastmoney only if not rate limited. Exact 1-minute completeness and terminal-bar validation remains mandatory. Never use historical daily close in place of a 14:50 bar. Fallback itself is not an assertion of available real market quotes; rerun actual probe and validate real evidence.

2026-10-30 16:43 second real probe: ETF vendor intermittently returned a stale prior trading date, despite earlier 16:37 current-date 510300 success. Every daily provider now explicitly requires the requested actual as-of session before being accepted; if stale, try independent alternate provider, else refuse paper evidence.
