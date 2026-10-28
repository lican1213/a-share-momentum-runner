"""SZSE per-fund historical ETF shares JSON fallback (exchange-native, not scraping).

Separate from AKShare whole-market XLSX request. Based on SZSE's
ShowReport/data?SHOWTYPE=JSON&CATALOGID=scsj_fund_jjgm.
The JSON field current_size is officially displayed in 10,000 shares:
convert it ONCE. TLS verification remains enabled.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Callable

URL = "https://www.szse.cn/api/report/ShowReport/data"
LANDING = "https://www.szse.cn/market/fund/volume/etf/index.html"


def parse_szse_page(payload, code: str, from_date: str, thru_date: str):
    """(records, pages). Fail closed on schema change and contradictory duplicates."""
    if not isinstance(payload,list) or not payload or not isinstance(payload[0],dict):
        raise ValueError("SZSE response is not the documented JSON array")
    block=payload[0]
    if block.get("error"):
        raise ValueError(f"SZSE declared an error: {str(block['error'])[:160]}")
    rows=block.get("data",[])
    if not isinstance(rows,list):
        raise ValueError("SZSE data is not an array")
    page_count=int((block.get("metadata") or {}).get("pagecount",1) or 1)
    if not 1<=page_count<=250:
        raise ValueError("invalid pagecount")
    parsed={}
    for item in rows:
        if not isinstance(item,dict):
            raise ValueError("SZSE bad row type")
        sym=str(item.get("fund_code","")).zfill(6)
        if sym != code:
            continue
        d=str(item.get("size_date","")).strip()[:10]
        try:
            date.fromisoformat(d)
        except ValueError:
            raise ValueError(f"SZSE bad trading date: {d}") from None
        if not from_date<=d<=thru_date:
            raise ValueError(f"SZSE trading date outside request: {d}")
        raw=str(item.get("current_size","")).replace(",","").strip()
        try:
            ten_thousands=Decimal(raw)
        except (InvalidOperation,TypeError,ValueError):
            raise ValueError(f"SZSE invalid share count: {raw}") from None
        if not ten_thousands.is_finite() or ten_thousands<0:
            raise ValueError("SZSE shares negative/nonfinite")
        shares=format(ten_thousands*10000,"f")
        if d in parsed and parsed[d]!=shares:
            raise ValueError("SZSE duplicate-date conflict")
        parsed[d]=shares
    return parsed,page_count


def fetch_one_szse_fund(code: str, start: str, end: str, *, getter: Callable | None = None,
                        max_pages: int = 32):
    """Retrieve *dated* raw-share units, with all-page completeness validation."""
    if code!="159919":
        raise ValueError("this fallback is scoped to core SZSE 159919")
    if date.fromisoformat(start)>date.fromisoformat(end):
        raise ValueError("reversed date range")
    if (date.fromisoformat(end)-date.fromisoformat(start)).days>100:
        raise ValueError("partition into <=100-day requests")
    if getter is None:
        import requests
        session=requests.Session()
        def getter(url, *, params, headers, timeout):
            last=None
            for i in range(3):
                try:
                    r=session.get(url,params=params,headers=headers,timeout=timeout)
                    r.raise_for_status()
                    return r.json()
                except (requests.RequestException, ValueError) as exc:
                    last=exc
                    if i<2:
                        import time
                        time.sleep(1+i)
            raise RuntimeError(f"SZSE JSON endpoint unavailable: {last}")
    headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
             "Referer":LANDING,"Accept":"application/json, text/javascript, */*",
             "X-Requested-With":"XMLHttpRequest"}
    out={}
    total_pages=None
    for page in range(1,max_pages+1):
        params={"SHOWTYPE":"JSON","CATALOGID":"scsj_fund_jjgm","TABKEY":"tab1",
                "txtDm":code,"txtStart":start,"txtEnd":end,"jjlb":"ETF",
                "tab1PAGENO":str(page)}
        payload=getter(URL,params=params,headers=headers,timeout=18)
        data,pages=parse_szse_page(payload,code,start,end)
        if total_pages is None:total_pages=pages
        if pages != total_pages:raise ValueError("SZSE pagecount changed during retrieval")
        for d,v in data.items():
            if d in out and out[d]!=v:
                raise ValueError("conflicting SZSE share counts across pages")
            out[d]=v
        if page>=total_pages:
            return out
    raise RuntimeError("SZSE more pages than configured maximum")
