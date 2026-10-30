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
