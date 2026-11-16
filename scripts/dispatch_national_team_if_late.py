"""Optional independent clock; run on a separate host, not GitHub Actions.

GH_TOKEN is supplied by that host's secret store. No repository writes.
"""
from datetime import datetime, time, timedelta, timezone
import json
import os
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

BJ = ZoneInfo("Asia/Shanghai")
API = "https://api.github.com/repos/lican1213/a-share-momentum-runner/actions/workflows/national-team-live.yml"
SLOTS = (time(7,50),time(9,15),time(16,20))
ACTIVE = {"queued","in_progress","waiting","pending","requested"}


def evaluate(now,runs):
    local=now.astimezone(BJ)
    if local.weekday()>=5:
        return "SKIP_WEEKEND"
    slots=[datetime.combine(local.date(),slot,BJ) for slot in SLOTS]
    eligible=[slot for slot in slots if slot+timedelta(minutes=15)<=local]
    if not eligible or local-eligible[-1]>timedelta(minutes=55):
        return "OUTSIDE_WATCHDOG_WINDOW"
    start=eligible[-1]
    active=[run for run in runs if run.get("status") in ACTIVE]
    if active:
        # A queued or running job may be stuck; don't silently call it healthy
        # or dispatch another job behind it in the same concurrency group.
        recent=[r for r in active if local-datetime.fromisoformat(
            r["created_at"].replace("Z","+00:00"))<=timedelta(minutes=55)]
        return "ACTIVE_ROOT_ALREADY_EXISTS" if recent else "ROOT_ACTIVE_STALLED"
    for run in runs:
        created=datetime.fromisoformat(run["created_at"].replace("Z","+00:00"))
        if start<=created<=local and run.get("conclusion")=="success":
            return "ROOT_SLOT_ALREADY_SUCCEEDED"
    return "DISPATCH_MISSING_ROOT_SLOT"


def request(path,token,body=None):
    req=Request(API+path, data=json.dumps(body).encode() if body is not None else None,
                headers={"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json",
                         "Content-Type":"application/json","User-Agent":"nt-root-watchdog"},
                method="POST" if body is not None else "GET")
    with urlopen(req,timeout=20) as res:
        raw=res.read()
        return res.status,json.loads(raw) if raw else {}


def main():
    token=os.environ.get("GH_TOKEN")
    if not token:
        raise SystemExit("GH_TOKEN missing; configure Actions:write in external secret store")
    now=datetime.now(timezone.utc)
    _,data=request("/runs?branch=main&per_page=50",token)
    decision=evaluate(now,data["workflow_runs"])
    print(now.astimezone(BJ).isoformat(),decision,flush=True)
    if decision=="ROOT_ACTIVE_STALLED":
        raise SystemExit(3)
    if decision=="DISPATCH_MISSING_ROOT_SLOT":
        status,_=request("/dispatches",token,{"ref":"main"})
        print("ROOT_DISPATCH_HTTP",status,flush=True)
        if status not in (200,201,204):
            raise SystemExit(2)
    # Acceptance of dispatch is not a successful or timely market run.
if __name__=="__main__":
    main()
