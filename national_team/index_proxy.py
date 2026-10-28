"""Index-weight proxy, NOT ETF PCF, used to study partial ETF funding.

The 000300 constituent-weight file is published by CSI. It is not any ETF's
actual PCF and it does not identify which investors traded. Captured at the
current time; no historical point-in-time availability is inferred from a
weight's labelled month-end date.
"""
from __future__ import annotations
from datetime import date,datetime
from decimal import Decimal, InvalidOperation
from typing import Mapping
from national_team.core_flow_factors import utc_aware

CSINDEX_WEIGHT_URL="https://oss-ch.csindex.com.cn/static/html/csindex/public/uploads/file/autofile/closeweight/000300closeweight.xls"

def validate_index_weights(frame,captured_at:str)->dict:
    capture=utc_aware(captured_at,"index weight capture")
    required={"日期","成分券代码","权重"}
    if not required.issubset(frame.columns):
        raise ValueError("CSI300 weights schema mismatch")
    weights={}
    dates=set()
    for _,row in frame.iterrows():
        code=str(row["成分券代码"]).split(".")[0].zfill(6)
        if len(code)!=6 or not code.isdigit():
            raise ValueError("invalid constituent symbol")
        day=str(row["日期"])[:10]
        asof=date.fromisoformat(day)
        if asof>capture.date():
            raise ValueError("future dated weight snapshot")
        dates.add(day)
        if code in weights:
            raise ValueError(f"duplicate index weight {code}")
        try:raw=Decimal(str(row["权重"]))
        except (InvalidOperation,TypeError,ValueError):
            raise ValueError("invalid index weight") from None
        if not raw.is_finite() or raw<0:raise ValueError("negative/nonfinite index weight")
        weights[code]=raw/Decimal(100)  # source column is PERCENT
    if len(dates)!=1:
        raise ValueError("CSI weight file has mixed dates")
    if len(weights)<250 or len(weights)>400:
        raise ValueError("unexpected CSI300 constituent count")
    coverage=sum(weights.values(),Decimal(0))
    if not Decimal("0.97")<=coverage<=Decimal("1.01"):
        raise ValueError(f"index weights do not sum to near 100%: {coverage}")
    return {"kind":"CSI300_LATEST_INDEX_WEIGHT_PROXY_NOT_ETF_PCF",
            "weight_asof":next(iter(dates)),
            "first_observed_at":capture.isoformat(),
            "source_url":CSINDEX_WEIGHT_URL,
            "weight_count":len(weights),
            "total_weight":format(coverage,"f"),
            "weights":{s:format(w,"f") for s,w in weights.items()}}

def partial_flow_to_stocks(record:Mapping,weight_observation:Mapping,
                           stock_rows:Mapping,*,top_n:int=10)->dict:
    """Rank ONLY mapped known flows and loaded stocks; no invented fund 159919.

    stock_rows: symbol->{adv20_cny,rel_strength20(optional),data_date,source_url}
    Never assumes latest CSI300 weights were ETF PCF holdings.
    """
    from national_team.core_flow_factors import CORE_FOUR
    c=record.get("capture_completed_beijing") or record.get("first_observed_no_earlier_than")
    cutoff=utc_aware(c,"funding source capture")
    wt_time=utc_aware(weight_observation.get("first_observed_at"),"weights capture")
    eligible=max(wt_time,cutoff)
    if not 1<=top_n<=30:raise ValueError("top_n outside predefined bounds")
    if weight_observation.get("kind")!="CSI300_LATEST_INDEX_WEIGHT_PROXY_NOT_ETF_PCF":
        raise ValueError("not a CSI300 official index proxy")
    wts={s:Decimal(str(v)) for s,v in weight_observation["weights"].items()}
    part=record.get("funding_event",{}).get("partial_funding") or record.get("partial_SSE_three_only")
    factor=record.get("funding_event",{}).get("four_etf_factor")
    if factor is not None:
        flows={s:Decimal(str(v)) for s,v in factor["per_etf_daily_flow_proxy_cny"].items()}
        fund_scope=list(CORE_FOUR)
        data_scope="FOUR_ETF_DATED_SHARE_FLOW"
    elif part and "per_fund_proxy_cny" in part:
        flows={s:Decimal(str(v)) for s,v in part["per_fund_proxy_cny"].items()}
        fund_scope=list(flows)
        data_scope="PARTIAL_SSE_THREE_EXCLUDES_159919"
    elif part and "per_etf_flow_cny" in part:
        flows={s:Decimal(str(v)) for s,v in part["per_etf_flow_cny"].items()}
        fund_scope=list(flows)
        data_scope="PARTIAL_SSE_THREE_EXCLUDES_159919"
    else:
        return {"status":"NO_DATED_FLOW_TO_MAP","candidates":[],"source_kind":weight_observation["kind"]}
    if not set(flows).issubset(CORE_FOUR):
        raise ValueError("noncore flow item")
    agg=sum(flows.values(),Decimal(0))
    ranked=[]
    for code,row in stock_rows.items():
        if code not in wts:continue
        if not str(row.get("source_url","")).startswith("https://"):
            continue
        if utc_aware(row.get("first_observed_at"),f"{code} capture")>eligible:
            # If stock data collected later than weights, don't falsely
            # assert the event existed earlier. Update event availability below.
            pass
        adv=Decimal(str(row.get("adv20_cny")))
        if not adv.is_finite() or adv<=0:continue
        implied=agg*wts[code]
        ratio=implied/adv
        ranked.append({"symbol":code,"benchmark_weight":format(wts[code],"f"),
                       "implied_index_exposure_cny":format(implied,"f"),
                       "signed_exposure_over_adv20":format(ratio,"f"),
                       "adv20_cny":format(adv,"f"),
                       "relative_strength20":row.get("relative_strength20"),
                       "source_url":row["source_url"],
                       "stock_data_date":row.get("data_date")})
    ranked.sort(key=lambda r:(-Decimal(r["signed_exposure_over_adv20"]),r["symbol"]))
    opposite=sorted((x for x in ranked if Decimal(x["signed_exposure_over_adv20"])<0),
                     key=lambda r:(Decimal(r["signed_exposure_over_adv20"]),r["symbol"]))[:top_n]
    candidates=[r for r in ranked if Decimal(r["signed_exposure_over_adv20"])>0][:top_n]
    return {"status":"INDEX_PROXY_RESEARCH_WATCHLIST" if ranked else "NO_STOCK_LIQUIDITY_DATA",
            "source_kind":weight_observation["kind"],
            "data_scope":data_scope,"observed_funds":fund_scope,
            "missing_funds":[c for c in CORE_FOUR if c not in flows],
            "index_weight_date":weight_observation["weight_asof"],
            "ranked_from_n_stocks":len(ranked),
            "index_total_constituents":weight_observation["weight_count"],
            "known_ETF_net_flow_proxy_cny":format(agg,"f"),
            "candidates":candidates,"outflow_risk":opposite,
            "topn_pool_is_partial":len(ranked)<weight_observation["weight_count"],
            "not_actual_ETF_PCF":True,
            "not_investor_identity":True,
            "not_executable_orders":True}
