"""Recover exact observed finalized bars from append-only V5 evidence."""
from datetime import datetime,time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
import json
from national_team.left_entry_v4 import digest

BJ=ZoneInfo("Asia/Shanghai")

def _values(row):
    vals=tuple(Decimal(str(row[k])) for k in ("open","high","low","close"))
    o,h,l,c=vals
    if any(not x.is_finite() or x<=0 for x in vals) or l>min(o,c) or h<max(o,c):
        raise ValueError("invalid OHLC")
    return vals

def recover(seen, codes, root, *, start, cutoff, observed_at):
    now=datetime.fromisoformat(observed_at).astimezone(BJ)
    by_symbol=seen.setdefault("bars_by_symbol",{})
    existing={c:{b["date"]:b for b in by_symbol.get(c,[])} for c in codes}
    proposed={}
    conflicts=set()
    # Recent immutable snapshots cover all active event windows; avoid an
    # unbounded read on every run as the repository accumulates evidence.
    paths=sorted(Path(root).glob("*/*.json"),key=lambda p:(
        p.parent.name,int(p.stem.split("-")[0]) if p.stem.split("-")[0].isdigit() else 0,p.name),reverse=True)[:16]
    for path in paths:
        batch=json.loads(path.read_text(encoding="utf-8"))
        for event in batch.get("results",[]):
            source=event.get("source_new_ohlc") or {}
            sha=event.get("source_new_ohlc_sha256")
            if not sha or digest(source)!=sha:
                continue
            stamp=source.get("first_observed_at") or source.get("capture_time")
            if not stamp:
                continue
            captured=datetime.fromisoformat(stamp.replace("Z","+00:00"))
            if captured.utcoffset() is None:
                continue
            captured=captured.astimezone(BJ)
            if captured>now:
                continue
            for code in codes:
                for row in source.get("bars_by_symbol",{}).get(code,[]):
                    day=row["date"]
                    if not start<day<=cutoff or day>captured.date().isoformat():
                        continue
                    if day==captured.date().isoformat() and captured.time()<time(15,5):
                        continue
                    if day in existing[code]:
                        continue
                    try:
                        value=_values(row)
                    except (ValueError,ArithmeticError,KeyError,TypeError):
                        continue
                    key=(code,day)
                    if key in proposed and value!=proposed[key][0]:
                        conflicts.add(key)
                    elif key not in proposed:
                        # Preserve the original bar source across repeated recovery.
                        origin = next((r for r in source.get("archived_bar_recovery",{}).get(code,[])
                                       if r["date"] == day), None)
                        segment = source.get("fallback_segments",{}).get(code,{})
                        vendor = segment if day in segment.get("dates",[]) else {
                            k:source.get(k,{}).get(code) for k in ("source_url","source_sha256")}
                        proposed[key]=(value,row,origin or {"date":day,"path":str(path),
                            "source_capture_time":stamp,"source_snapshot_sha256":sha,
                            "source_url":vendor.get("source_url"),"source_sha256":vendor.get("source_sha256")})
    for (code,day),(_,row,provenance) in proposed.items():
        if (code,day) in conflicts:
            continue
        existing[code][day]=row
        seen.setdefault("archived_bar_recovery",{}).setdefault(code,[]).append(provenance)
    for code,rows in existing.items():
        if rows:
            by_symbol[code]=[r for _,r in sorted(rows.items())]
    if conflicts:
        seen["archive_recovery_conflicts"]=[f"{c}:{d}" for c,d in sorted(conflicts)]
    return seen
