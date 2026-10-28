"""Direct SSE daily cleared ETF share totals with bounded HTTPS requests.

Official SSE TOT_VOL is in 10,000 shares; this adapter multiplies ONCE.
AKShare fund_etf_scale_sse already converts to shares -- do NOT double-multiply.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation

URL="https://query.sse.com.cn/commonQuery.do"
PAGE="https://www.sse.com.cn/assortment/fund/etf/list/scale/"
SSE_FOUR=("510300","510310","510330")

def parse_sse_payload(payload,expected_day):
    if not isinstance(payload,dict) or not isinstance(payload.get("result"),list):
        raise ValueError("SSE result missing or invalid; never accept empty JSON as 0 shares")
    result={}
    for row in payload["result"]:
        if not isinstance(row,dict):raise ValueError("invalid SSE row")
        code=str(row.get("SEC_CODE","")).zfill(6)
        if code not in SSE_FOUR:continue
        asof=str(row.get("STAT_DATE","")).strip()[:10]
        if asof!=expected_day:continue
        try:
            raw=Decimal(str(row["TOT_VOL"]).replace(",",""))
        except (InvalidOperation,KeyError,ValueError,TypeError):
            raise ValueError(f"missing SSE TOT_VOL for {code}") from None
        if not raw.is_finite() or raw<=0:raise ValueError("SSE raw ETF shares invalid")
        number=raw*10000
        if code in result and result[code]!=str(number):
            raise ValueError(f"conflicting duplicate SSE {code}")
        result[code]=format(number,"f")
    return result

def fetch_sse_direct(day,*,getter=None,attempts=2,timeout=10):
    date.fromisoformat(day)
    if getter is None:
        import requests,time
        session=requests.Session()
        def getter(url,params,headers,timeout):
            response=session.get(url,params=params,headers=headers,timeout=timeout)
            response.raise_for_status()
            return response.json()
    headers={"Referer":"https://www.sse.com.cn/",
            "User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0 Safari/537.36"}
    params={"isPagination":"true","pageHelp.pageSize":"10000","pageHelp.pageNo":"1",
            "pageHelp.beginPage":"1","pageHelp.cacheSize":"1","pageHelp.endPage":"1",
            "sqlId":"COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L",
            "STAT_DATE":day}
    import time
    failure=None
    for attempt in range(attempts):
        try:
            raw=getter(URL,params,headers,timeout)
            return parse_sse_payload(raw,day)
        except Exception as exc:
            failure=exc
            if attempt+1<attempts:time.sleep(1)
    raise RuntimeError(f"SSE direct data unavailable after {attempts} bounded attempts: {failure}")
