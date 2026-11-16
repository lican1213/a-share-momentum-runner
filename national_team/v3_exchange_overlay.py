"""Consume exact-date verified exchange archives without backfilling clocks.

Preserve the independent external historical replay as a separate baseline.
No partial share basket, conflicting exchange observation or undated quote
is promoted to a complete official observation.
"""
from __future__ import annotations
import copy
import hashlib
import json
import math
from datetime import datetime
from pathlib import Path
from national_team.core_flow_factors import CORE_FOUR

def clock(value):
    d=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if d.utcoffset() is None:
        raise ValueError("timezone required")
    return d

def overlay(shares, nav, root, *, observed_at, index_sessions):
    now=clock(observed_at)
    candidates=[]
    for p in Path(root).glob("*/*.json"):
        raw=p.read_bytes()
        item=json.loads(raw)
        t=item.get("capture_completed_beijing")
        if item.get("unit")=="raw_shares" and t and clock(t)<=now:
            candidates.append((clock(t),str(p),item,hashlib.sha256(raw).hexdigest()))
    result_shares=copy.deepcopy(shares)
    result_nav=copy.deepcopy(nav)
    meta={"status":"NO_ARCHIVED_EXCHANGE_ROWS","share_dates":[],"nav_dates":[],
          "external_share_disagreements":[],"external_nav_disagreements":[]}
    if not candidates:
        return result_shares,result_nav,meta
    _,path,item,sha=max(candidates,key=lambda r:(r[0],r[1]))
    meta.update(status="EXCHANGE_OVERLAY",archive_path=path,archive_sha256=sha,
                archive_captured_at=item["capture_completed_beijing"])
    conflicts={(x.get("date"),x.get("code"),x.get("field"))
               for x in item.get("conflicts",[]) if isinstance(x,dict)}
    def group(day, funds,field):
        vals={}
        for code in CORE_FOUR:
            row=funds.get(code,{})
            stamp=row.get(f"{field}_first_observed_at")
            if not stamp or not row.get(f"{field}_source_path") or any(x[0]==day and x[1]==code for x in conflicts):
                return None
            try:
                value=float(row[field])
                if not math.isfinite(value) or value<=0 or clock(stamp)>now:
                    return None
            except (KeyError,TypeError,ValueError):
                return None
            vals[code]=value
        return vals
    for day,funds in sorted(item.get("observations_by_date",{}).items()):
        if day not in index_sessions:
            continue
        values=group(day,funds,"shares")
        if values is not None:
            previous=shares.get(day,{})
            different=[c for c in CORE_FOUR if c in previous and abs(previous[c]-values[c])>1]
            if different:
                meta["external_share_disagreements"].append({"date":day,"codes":different})
            result_shares[day]=values
            meta["share_dates"].append(day)
        values=group(day,funds,"nav")
        if values is not None:
            previous=nav.get(day,{})
            different=[c for c in CORE_FOUR if c in previous and abs(previous[c]["nav"]-values[c])>1e-6]
            if different:
                meta["external_nav_disagreements"].append({"date":day,"codes":different})
            result_nav[day]={c:{"nav":v,"published_at":funds[c]["nav_first_observed_at"],
                               "source_url":funds[c]["nav_source_path"],
                               "corporate_action":previous.get(c,{}).get("corporate_action","unknown")}
                             for c,v in values.items()}
            meta["nav_dates"].append(day)
    meta["complete_exchange_share_nav_dates"]=sorted(set(meta["share_dates"])&set(meta["nav_dates"]))
    return result_shares,result_nav,meta
