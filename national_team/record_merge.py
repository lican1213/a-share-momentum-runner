"""Append-only ETF source snapshot reconciliation across intermittent providers.

Preserves every source run, date, first-seen observation; conflicts are excluded,
not silently overwritten. A composite research factor is first knowable ONLY
after the last contributing observation has been archived.
"""
from __future__ import annotations
import argparse,glob,json,os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
from national_team.core_flow_factors import CORE_FOUR
from national_team.event_pipeline import reconcile_funding_snapshot,exchange_sessions


def merge_snapshot_records(records:list[tuple[str,dict]],asof:str,*,at:str)->dict:
    """merge immutable source records sorted by capture time."""
    all_rows={}; provenance={}; conflicts=[]; source_runs=[]
    ordered=sorted(records,key=lambda x:str(x[1].get("first_observed_no_earlier_than","")))
    for source_path,r in ordered:
        if not isinstance(r.get("observations_by_date"),dict):
            continue
        if str(r.get("asof_requested",""))>asof:continue
        run=str(r.get("run_id","unknown"))
        src_capture=str(r.get("capture_completed_beijing") or r.get("first_observed_no_earlier_than") or "")
        if not src_capture:continue
        source_runs.append({"run_id":run,"path":source_path,"capture":src_capture,
                            "collector_status":r.get("status")})
        for day,per_code in r["observations_by_date"].items():
            if day>asof or not isinstance(per_code,dict):continue
            for code,rec in per_code.items():
                if code not in CORE_FOUR or not isinstance(rec,dict) or "shares" not in rec:continue
                row=all_rows.setdefault(day,{}).setdefault(code,{})
                ref=provenance.setdefault(day,{}).setdefault(code,[])
                ref.append({"source_run":run,"file":source_path,"capture":src_capture,
                            "fields":[k for k in ("shares","nav") if k in rec]})
                for key in ("shares","nav"):
                    if key not in rec:continue
                    try:
                        num=Decimal(str(rec[key]))
                    except Exception:
                        conflicts.append({"date":day,"code":code,"field":key,"source":source_path,
                                          "reason":"malformed numeric"})
                        continue
                    if not num.is_finite() or num<=0:
                        conflicts.append({"date":day,"code":code,"field":key,"source":source_path,
                                          "reason":"nonpositive / nonfinite"})
                        continue
                    if key in row and Decimal(str(row[key]))!=num:
                        conflicts.append({"date":day,"code":code,"field":key,
                                          "previous":row[key],"incoming":str(num),
                                          "source":source_path})
                    elif key not in row:
                        row[key]=str(num)
                        row[f"{key}_source_path"]=source_path
                        row[f"{key}_first_observed_at"]=src_capture
    # If any date-code-field conflicts, censor the entire date-code record;
    # never choose a preferred version and pretend provenance is clean.
    exclude={(x["date"],x["code"]) for x in conflicts}
    for d,c in exclude:
        all_rows.get(d,{}).pop(c,None)
    for day in list(all_rows):
        if not all_rows[day]:
            del all_rows[day]
    out={"schema":1,"status":"MERGED_SOURCES_NO_FACTOR","run_id":None,
         "asof_requested":asof,"run_attempt":None,
         "first_observed_no_earlier_than":at,"capture_completed_beijing":at,
         "unit":"raw_shares","observations_by_date":all_rows,
         "sources_used":source_runs,"row_provenance":provenance,"conflicts":conflicts,
         "conflicted_date_code_pairs":len(exclude),
         "undated_SZSE_snapshots_excluded":True,
         "point_in_time_policy":"historical provider data first knowable at MAX source capture; no backwards signals",
         "national_team_identity_proven":False,"trade_orders_authorized":False}
    return out

def collect_merge(source_root:Path,out_root:Path,asof:str,run_id:str,attempt:str):
    now=datetime.now(ZoneInfo("Asia/Shanghai")).isoformat()
    filenames=sorted(source_root.glob("*/*.json"))
    parsed=[]
    for p in filenames:
        try:r=json.loads(p.read_text(encoding="utf-8"))
        except (OSError,ValueError):continue
        if str(r.get("asof_requested",""))<=asof:
            parsed.append((str(p),r))
    # Limit to most recent source versions but retain every raw record untouched.
    parsed.sort(key=lambda x:str(x[1].get("capture_completed_beijing","")),reverse=True)
    parsed=parsed[:100]
    merged=merge_snapshot_records(parsed,asof,at=now)
    merged["run_id"]=run_id;merged["run_attempt"]=attempt
    try:
        sessions=exchange_sessions(asof,lookback_days=21)
        merged["funding_event"]=reconcile_funding_snapshot(merged,sessions)
        merged["status"]=merged["funding_event"]["status"]
    except Exception as exc:
        merged["status"]="MERGE_DONE_CALENDAR_UNAVAILABLE"
        merged["calendar_error"]=f"{type(exc).__name__}:{str(exc)[:240]}"
    target=out_root/asof/f"{run_id}-a{attempt}.json"
    if target.exists():raise FileExistsError("refuse to overwrite merged run")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(merged,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return target,merged

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--asof",default=datetime.now(ZoneInfo("Asia/Shanghai")).date().isoformat())
    parser.add_argument("--source-root",default="records/national_team_etf")
    parser.add_argument("--out",default="records/national_team_merged")
    args=parser.parse_args()
    run=os.environ.get("GITHUB_RUN_ID","local")
    attempt=os.environ.get("GITHUB_RUN_ATTEMPT","1")
    target,r=collect_merge(Path(args.source_root),Path(args.out),args.asof,run,attempt)
    print(json.dumps({"merge_status":r["status"],
                      "source_runs":len(r["sources_used"]),
                      "conflict_pairs":r["conflicted_date_code_pairs"],
                      "four_complete_days":len(r.get("funding_event",{}).get("complete_four_days",[])),
                      "merged_record":str(target)},ensure_ascii=False))
if __name__=="__main__":main()
