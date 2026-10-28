from national_team.ohlc_execution_guard import conservative_ohlc_bar

def test_limit_up_one_price_with_positive_volume_is_not_assumed_filled():
    x=conservative_ohlc_bar(11,11,11,11,1000,10)
    assert x["entry_blocked"] and x["exit_blocked"] is False

def test_limit_down_one_price_blocks_exit():
    x=conservative_ohlc_bar(9,9,9,9,1000,10)
    assert x["exit_blocked"] and x["entry_blocked"] is False

def test_normal_day_is_still_an_unconfirmed_fill():
    x=conservative_ohlc_bar(10,11,9,10.4,10000,10)
    assert x["exact_order_fill_known"] is False
    assert x["entry_blocked"] is False

def test_no_volume_blocks_both_sides():
    x=conservative_ohlc_bar(10,10,10,10,0,10)
    assert x["entry_blocked"] and x["exit_blocked"]
