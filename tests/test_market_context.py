"""No-network tests for market context calculation and stale-source failure gates."""
from datetime import date
import numpy as np
import pandas as pd
import pytest

from market_context import compute_index, compute_breadth


def test_index_requires_matching_asof_and_ma60():
    prices = 4000 + np.arange(90) * 2.0
    raw = pd.DataFrame({"日期": pd.bdate_range(end="2026-10-28", periods=90),
                        "收盘": prices})
    x = compute_index(raw, date(2026, 10, 28))
    assert x["above_ma20"] and x["above_ma60"]
    assert set(x["returns"]) == {"5d", "10d", "20d"}
    with pytest.raises(ValueError, match="stale/short"):
        compute_index(raw, date(2026, 10, 29))


def test_incomplete_breadth_rejected():
    raw = pd.DataFrame({"代码": ["600036", "600519"],
                        "名称": ["A", "B"], "涨跌幅": [1.0, -1.0]})
    with pytest.raises(ValueError, match="not full A-share"):
        compute_breadth(raw, date(2026, 10, 28))
