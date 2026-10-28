"""Regression check for quantstats 0.0.86 DatetimeIndex requirement.

Synthetic RETURNS test only; it is not market performance.
"""
import pandas as pd
import quantstats as qs


def test_quantstats_drawdown_with_trade_sequence_datetime_index():
    returns = pd.Series(
        [0.02, -0.01, -0.03, 0.02],
        index=pd.date_range("2000-01-01", periods=4, freq="D"),
    )
    result = qs.stats.max_drawdown(returns)
    assert isinstance(result, float)
    assert -1 < result < 0
