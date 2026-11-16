"""Explicit API migration only: preserve unadjusted price semantics."""
def named_api(ak, current, legacy):
    # AKShare's module __getattr__ may deliberately raise AttributeError for
    # removed APIs. Prefer the documented current name; legacy only if absent.
    func = getattr(ak, current, None)
    if callable(func):
        return func
    func = getattr(ak, legacy, None)
    if not callable(func):
        raise AttributeError(f"AKShare lacks both {current} and {legacy}")
    return func

def sina_stock_daily(ak, **kwargs):
    return named_api(ak, "stock_zh_a_hist_sina", "stock_zh_a_daily")(**kwargs)

def eastmoney_stock_daily(ak, **kwargs):
    return named_api(ak, "stock_zh_a_hist_em", "stock_zh_a_hist")(**kwargs)
