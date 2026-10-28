# A-share 3-day momentum runner

Automated, auditable research workflow for China A-shares. This repository has no broker credentials and never executes orders.

**Status:** initializing. An uploaded script or scheduled YAML file is **not** proof of successful execution. Inspect GitHub Actions logs and artifacts before treating any signals or backtest results as validated.

Core rules: 0-3 candidates, rising momentum breakouts only, planned T+3 exit, actual T+1 and price-limit constraints, no lookahead, no invented data, never rewrite an original trade signal. Reproducibility and failure-closed behavior take precedence over always emitting a buy price.

Data: AKShare official upstream at https://github.com/akfamily/akshare
Backtesting: AKQuant at https://github.com/akfamily/akquant
Performance diagnostics: QuantStats at https://github.com/ranaroussi/quantstats
