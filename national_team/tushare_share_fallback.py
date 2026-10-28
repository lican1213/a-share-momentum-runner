"""Dated ETF share cross-check using the documented Tushare etf_share_size schema.

Provider total_share is in 10,000 shares. This is a secondary service,
not an exchange-native filing. No credentials are stored in source.
"""
from datetime import date
from decimal import Decimal

URL="https://tushare.pro/document/2?doc_id=408"
FOUR=("510300","510310","510330","159919")

def normalize(frame, start, end):
    keys={"trade_date","ts_code","total_share","exchange"}
    if not keys.issubset(frame.columns):
        raise ValueError("secondary share source schema invalid")
    out={}
    for _,row in frame.iterrows():
        symbol=str(row["ts_code"])
        code=symbol[:6]
        if code not in FOUR:continue
        suffix=".SZ" if code=="159919" else ".SH"
        expected="SZSE" if code=="159919" else "SSE"
        if symbol!=code+suffix or str(row["exchange"])!=expected:
            raise ValueError("ticker/exchange mismatch")
        day=str(row["trade_date"]).replace("-","")[:8]
        if not (len(day)==8 and day.isdigit()):
            raise ValueError("invalid source trade date")
        iso=date.fromisoformat(day[:4]+"-"+day[4:6]+"-"+day[6:]).isoformat()
        if not start<=iso<=end:
            raise ValueError("out-of-window ETF shares")
        qty=Decimal(str(row["total_share"]).replace(",",""))
        if not qty.is_finite() or qty<=0:
            raise ValueError("invalid ETF shares")
        val=format(qty*10000,"f")
        previous=out.setdefault(iso,{}).get(code)
        if previous is not None and previous!=val:
            raise ValueError("duplicate conflicting ETF shares")
        out[iso][code]=val
    return out
