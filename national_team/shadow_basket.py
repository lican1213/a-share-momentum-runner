"""Fixed 35-fund third-party observation, not a core indicator or trade signal."""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from national_team.core_flow_factors import CORE_FOUR, utc_aware
from national_team.left_entry_v4 import d, digest

BJ = ZoneInfo("Asia/Shanghai")
UPSTREAM = "wj624/national-team-etf-flow"
# Freeze membership, rather than allowing the upstream dashboard to redefine history.
GROUPS = {
    "沪深300": (*CORE_FOUR, "515330"),
    "中证A500": ("159338","159361","159352","563360","512050","159351","563220","563800"),
    "科创板50": ("588080","588000","588050"),
    "中证1000": ("512100","159845","560010","159629","159633"),
    "创业板": ("159915","159952","159977"),
    "上证50": ("510050","510100"),
    "创业板50": ("159949",),
    "中证500": ("510500","512500","159922"),
    "深证100": ("159901",),
    "中证800": ("515800",),
    "上证180": ("510180",),
    "上证180金融": ("510230",),
    "MSCI中国A50": ("560050",),
}
MEMBERS = {c: group for group, codes in GROUPS.items() for c in codes}


def observe(payload, *, observed_at, source_commit, source_sha256):
    clock = utc_aware(observed_at, "capture").astimezone(BJ)
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("source identity missing")
    day = datetime.strptime(payload["asof"], "%Y-%m-%d").date()
    generated = datetime.strptime(payload["generated"], "%Y-%m-%d %H:%M").replace(tzinfo=BJ)
    if (day.weekday() >= 5 or generated.date() < day or generated > clock
            or day > clock.date() or (day == clock.date() and clock.time() < time(15, 5))):
        raise ValueError("future or invalid upstream timestamp")
    entries = payload["etfs"]
    codes = [row["c"] for row in entries]
    if len(codes) != len(set(codes)) or set(codes) != set(MEMBERS):
        raise ValueError("fixed basket membership mismatch")
    rows = {}
    for row in entries:
        code = row["c"]
        if row["cat"] != MEMBERS[code]:
            raise ValueError("category mismatch")
        change, nav, shares, flow = (d(row[k], k) for k in ("dsh","nav","share","today"))
        if nav <= 0 or shares <= 0 or shares-change <= 0:
            raise ValueError("invalid shares or NAV")
        if abs(change*nav-flow) > Decimal("0.12"):
            raise ValueError("flow/units mismatch")
        rows[code] = {"group": MEMBERS[code], "shares_100m_rounded": str(shares),
                      "share_change_100m_rounded": str(change), "nav_cny": str(nav),
                      "net_100m_cny_rounded": str(flow)}
    total = sum(d(x["net_100m_cny_rounded"], "flow") for x in rows.values())
    reported = d(payload["today"]["net"], "total")
    if abs(total-reported) > Decimal("1.80"):
        raise ValueError("aggregate rounding mismatch")
    def group(codes):
        return {"net_100m_cny_rounded": str(sum(d(rows[c]["net_100m_cny_rounded"],"flow") for c in codes)),
                "negative_funds": sum(d(rows[c]["share_change_100m_rounded"],"change") < 0 for c in codes),
                "funds": len(codes)}
    result = {"schema": 1, "status": "THIRD_PARTY_OBSERVED_NOT_OFFICIAL_PIT",
              "basket": "SHADOW35_20261126_V1", "session": day.isoformat(),
              "first_observed_at": clock.isoformat(), "upstream_generated_unverified": payload["generated"], "upstream_generated_timezone_verified": False,
              "source_commit": source_commit, "source_sha256": source_sha256,
              "source_url": f"https://github.com/{UPSTREAM}/blob/{source_commit}/latest.json",
              "groups": {g: group(cs) for g,cs in GROUPS.items()},
              "core_four": group(CORE_FOUR), "expanded_ex_core": group([c for c in MEMBERS if c not in CORE_FOUR]),
              "all_funds": group(MEMBERS), "upstream_reported_total_100m_cny": str(reported),
              "rows": rows, "per_fund_official_dates_verified": False,
              "investor_identity_attributable": False, "trade_authorized": False, "broker_orders": []}
    result["snapshot_sha256"] = digest(result)
    return result


def _download(url):
    request = Request(url, headers={"User-Agent":"national-team-shadow-research/1",
                                    "Accept":"application/vnd.github+json"})
    with urlopen(request, timeout=12) as response:
        raw = response.read(1000001)
    if len(raw)>1000000:
        raise ValueError("oversize source")
    return raw


def fetch_snapshot():
    errors = []
    def record(stage, exc):
        errors.append({"stage":stage,"type":type(exc).__name__,
                       "http_status":exc.code if isinstance(exc,HTTPError) else None})
    try:
        sha = json.loads(_download(f"https://api.github.com/repos/{UPSTREAM}/commits/main"))["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}",sha):
            raise ValueError("invalid upstream commit")
    except (OSError,ValueError,KeyError,TypeError) as exc:
        record("resolve_api",exc)
        try:
            out = subprocess.run(["git","ls-remote",f"https://github.com/{UPSTREAM}.git",
                                  "refs/heads/main"],check=True,capture_output=True,
                                 text=True,timeout=12,env={**os.environ,"GIT_TERMINAL_PROMPT":"0"})
            fields=out.stdout.strip().split()
            if len(fields)!=2 or fields[1]!="refs/heads/main" or not re.fullmatch(r"[0-9a-f]{40}",fields[0]):
                raise ValueError("invalid pinned remote head")
            sha=fields[0]
        except (OSError,ValueError,subprocess.SubprocessError) as exc:
            record("resolve_git",exc)
            return None,None,errors
    try:
        raw=_download(f"https://raw.githubusercontent.com/{UPSTREAM}/{sha}/latest.json")
        return sha,raw,errors
    except (OSError,ValueError) as exc:
        record("pinned_raw",exc)
    try:
        obj=json.loads(_download(f"https://api.github.com/repos/{UPSTREAM}/contents/latest.json?ref={sha}"))
        raw=base64.b64decode(obj["content"].replace("\n",""),validate=True)
        if len(raw)>1000000 or hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()!=obj["sha"]:
            raise ValueError("Git blob mismatch")
        return sha,raw,errors
    except (OSError,ValueError,KeyError,TypeError) as exc:
        record("pinned_contents",exc)
        return sha,None,errors


def capture(root=Path("records/national_team_shadow_basket")):
    # Same collector/cadence; a bounded public-provider fallback, no credentials.
    sha,raw,errors=fetch_snapshot()
    try:
        if raw is None:
            raise ValueError("no pinned source retrieved")
        result = observe(json.loads(raw), observed_at=datetime.now(BJ).isoformat(),
                         source_commit=sha, source_sha256=hashlib.sha256(raw).hexdigest())
        result["source_attempt_errors"]=errors
    except (OSError, ValueError, KeyError, TypeError, ArithmeticError) as exc:
        result = {"schema":1,"status":"SOURCE_UNAVAILABLE","basket":"SHADOW35_20261126_V1",
                  "first_observed_at":datetime.now(BJ).isoformat(),"error_type":type(exc).__name__,
                  "source_attempt_errors":errors,"source_commit":sha,
                  "trade_authorized":False,"broker_orders":[]}
    result.pop("snapshot_sha256",None)
    result["snapshot_sha256"]=digest(result)
    run, attempt = os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"]
    if not run.isdigit() or not attempt.isdigit():
        raise ValueError("invalid run identity")
    target = root / datetime.now(BJ).date().isoformat() / f"{run}-a{attempt}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x",encoding="utf-8") as handle:
        json.dump(result,handle,ensure_ascii=False,indent=2)
    print("SHADOW35", result["status"], target)


if __name__ == "__main__":
    capture()
