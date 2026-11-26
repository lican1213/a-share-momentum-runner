"""Published-vintage reconstruction, not exchange-level publication or OOS proof."""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import exchange_calendars as xc
from national_team.shadow_basket import MEMBERS, BJ
from national_team.core_flow_factors import CORE_FOUR, utc_aware
from national_team.left_entry_v4 import d

ROOT=Path(__file__).resolve().parents[1]
COMMON23=("159629","159845","159901","159915","159919","159922","159952","159977",
          "510050","510100","510180","510230","510300","510310","510330","510500",
          "512100","512500","515800","560010","560050","588050","588080")
BASKETS={"COMMON23":COMMON23,"SHADOW34":tuple(c for c in MEMBERS if c!="159949"),
         "SHADOW35":tuple(MEMBERS)}
PAGES="MATCHED_SUCCESSFUL_PAGES_RUN_UPDATED_AT"
PUSH="MATCHED_SUCCESSFUL_REFRESH_PUSH_LOG"


def validate(vintage):
    for k in ("commit","blob_sha"):
        if not re.fullmatch(r"[0-9a-f]{40}",vintage[k]):
            raise ValueError("invalid pinned source")
    if type(vintage["run_id"]) is not int or vintage["run_id"]<=0:
        raise ValueError("missing run evidence")
    clock=utc_aware(vintage["available_at"],"server time").astimezone(BJ)
    day=date.fromisoformat(vintage["session"])
    if day.weekday()>=5 or clock<datetime.combine(day,time(15,0),BJ):
        raise ValueError("publication predates market close")
    if vintage["evidence"]==PUSH:
        if (type(vintage.get("job_id")) is not int or
                utc_aware(vintage["push_confirmed_at"],"push clock")>clock):
            raise ValueError("unverified push evidence")
    elif vintage["evidence"]!=PAGES:
        raise ValueError("commit timestamp alone is not publication")
    codes=[x["c"] for x in vintage["etfs"]]
    if len(codes)!=len(set(codes)):
        raise ValueError("duplicate member")
    if abs(sum(d(x["today"],"flow") for x in vintage["etfs"])-d(vintage["reported_total"],"total"))>Decimal(len(codes))*Decimal(".05")+Decimal(".05"):
        raise ValueError("reported total inconsistent")
    return clock,{x["c"]:x for x in vintage["etfs"]}


def measure(vintage, codes):
    clock,rows=validate(vintage)
    if not set(codes)<=set(rows):
        return None
    flows={};anomalies=[]
    for code in codes:
        row=rows[code]
        if row["cat"]!=MEMBERS[code]:
            raise ValueError("category mismatch")
        share,change,nav,flow=(d(row[k],k) for k in ("share","dsh","nav","today"))
        if share<=0 or nav<=0 or share-change<=0 or abs(change*nav-flow)>Decimal(".12"):
            anomalies.append({"code":code,"reason":"INVALID_OR_ACTION_AFFECTED_FLOW"})
        elif abs(change/(share-change))>Decimal(".30"):
            anomalies.append({"code":code,"reason":"LARGE_SHARE_JUMP_REVIEW"})
        flows[code]=flow
    return {"session":vintage["session"],"available_at":clock.isoformat(),
            "commit":vintage["commit"],"blob_sha":vintage["blob_sha"],"run_id":vintage["run_id"],
            "evidence":vintage["evidence"],"net_100m_cny_rounded":str(sum(flows.values())),
            "expanded_ex_core_100m_cny_rounded":str(sum(v for c,v in flows.items() if c not in CORE_FOUR)),
            "negative_funds_rounded":sum(x<0 for x in flows.values()),
            "members":len(codes),"review_flags":anomalies,
            "official_per_fund_publication_verified":False,"trade_authorized":False}


def select(vintages, codes, session, cutoff):
    cutoff=utc_aware(cutoff,"decision cutoff")
    candidates=[]
    for vintage in vintages:
        if vintage["session"]!=session or utc_aware(vintage["available_at"],"server time")>cutoff:
            continue
        row=measure(vintage,codes)
        if row is not None:
            candidates.append(row)
    # Later published corrections may inform later decisions, never earlier ones.
    return max(candidates,key=lambda x:utc_aware(x["available_at"],"available")) if candidates else None


def report(vintages):
    if len({v["commit"] for v in vintages})!=len(vintages):
        raise ValueError("duplicate vintage")
    cal=xc.get_calendar("XSHG")
    days=[x.date().isoformat() for x in cal.sessions_in_range("2026-10-30","2026-11-26")]
    out={}
    for name,codes in BASKETS.items():
        found={}
        for vintage in sorted(vintages,key=lambda v:utc_aware(v["available_at"],"server time")):
            if vintage["session"] not in days:
                raise ValueError("non-exchange session")
            row=measure(vintage,codes)
            if row is not None:
                found.setdefault(row["session"],row)
        for day,row in found.items():
            stamp=utc_aware(row["available_at"],"available")
            nextday=next((d for d in days if datetime.combine(date.fromisoformat(d),time(9,30),BJ)>stamp),None)
            row["next_open_session"]=nextday
            row["next_session_open_available"]=nextday is not None and days.index(nextday)==days.index(day)+1
        out[name]={"covered_sessions":len(found),"next_session_open_available":sum(x["next_session_open_available"] for x in found.values()),
                   "review_flagged_sessions":sum(bool(x["review_flags"]) for x in found.values()),
                   "missing_sessions":[day for day in days[:-1] if day not in found],
                   "first_complete_observed_vintages":found}
    return {"scope":"EXTERNAL_PUBLICATION_UPPER_BOUND_EXPLORATORY_NOT_OFFICIAL_PIT",
            "vintages":len(vintages),"baskets":out,"trade_authorized":False}


def load(root=ROOT):
    return [v for path in sorted((root/"research/shadow_pit").glob("vintages_*.json"))
            for v in json.loads(path.read_text(encoding="utf-8"))]


if __name__=="__main__":
    print(json.dumps(report(load()),ensure_ascii=False,indent=2))
