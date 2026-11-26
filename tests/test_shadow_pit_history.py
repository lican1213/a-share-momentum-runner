"""Real published vintages plus adversarial time, membership, and provider tests."""
import base64
import copy
import hashlib
import json
from types import SimpleNamespace
from urllib.error import HTTPError

import pytest

from national_team import shadow_basket as shadow
from scripts.research_shadow_pit_history import BASKETS, load, report, select, validate


def test_real_vintage_coverage(capsys):
    result=report(load())
    assert result["vintages"]==40
    assert result["outside_study_window_vintages"]==2
    assert result["baskets"]["COMMON23"]["covered_sessions"]==19
    assert result["baskets"]["SHADOW34"]["covered_sessions"]==10
    assert result["baskets"]["SHADOW35"]["covered_sessions"]==2
    assert result["baskets"]["COMMON23"]["numerically_complete_sessions"]==17
    assert result["baskets"]["SHADOW34"]["numerically_complete_sessions"]==8
    assert result["baskets"]["SHADOW35"]["numerically_complete_sessions"]==2
    assert result["baskets"]["COMMON23"]["first_complete_observed_vintages"]["2026-11-02"]["next_open_session"]=="2026-11-04"
    assert result["baskets"]["SHADOW35"]["first_complete_observed_vintages"]["2026-11-24"]["next_open_session"]=="2026-11-26"
    assert result["trade_authorized"] is False
    with capsys.disabled():
        print("SHADOW_PIT_RESULT",json.dumps({k:{a:b for a,b in v.items() if a!="first_complete_observed_vintages"} for k,v in result["baskets"].items()},ensure_ascii=False))


def test_cannot_backfill_new_members_or_revision():
    vs=load()
    assert select(vs,BASKETS["SHADOW35"],"2026-11-24","2026-11-25T09:30:00+08:00") is None
    old=select(vs,BASKETS["SHADOW34"],"2026-11-24","2026-11-25T09:30:00+08:00")
    assert old["commit"].startswith("a7a1314")
    new=select(vs,BASKETS["SHADOW35"],"2026-11-24","2026-11-25T15:26:00+08:00")
    assert new["commit"].startswith("ecec111")
    assert select(vs,BASKETS["SHADOW34"],"2026-11-12","2026-11-13T09:30:00+08:00") is None


@pytest.mark.parametrize("case",["commit_only","future","duplicate","wrong_total","no_run","bad_sha"])
def test_bad_vintage(case):
    v=copy.deepcopy(load()[0])
    if case=="commit_only":v["evidence"]="COMMIT_AUTHOR_DATE"
    elif case=="future":v["available_at"]="2026-10-01T00:00:00Z"
    elif case=="duplicate":v["etfs"].append(v["etfs"][0])
    elif case=="wrong_total":v["reported_total"]=999999
    elif case=="no_run":v["run_id"]=0
    elif case=="bad_sha":v["blob_sha"]="bad"
    with pytest.raises(ValueError):
        validate(v)


def test_fallback_pins_commit_and_verifies_blob(monkeypatch):
    raw=b'{"example":true}'
    sha="a"*40
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    calls=[]
    def download(url):
        calls.append(url)
        if "/commits/main" in url or "raw.githubusercontent" in url:
            raise HTTPError(url,403,"forbidden",None,None)
        return json.dumps({"sha":blob,"content":base64.b64encode(raw).decode()}).encode()
    monkeypatch.setattr(shadow,"_download",download)
    monkeypatch.setattr(shadow.subprocess,"run",lambda *a,**kw:SimpleNamespace(stdout=sha+"\trefs/heads/main\n"))
    got,data,errors=shadow.fetch_snapshot()
    assert got==sha and data==raw and len(errors)==2
    assert sha in calls[-1] and errors[0]["http_status"]==403
    monkeypatch.setattr(shadow,"_download",lambda url:(_ for _ in ()).throw(HTTPError(url,404,"missing",None,None)))
    assert shadow.fetch_snapshot()[1] is None


def test_zero_placeholder_and_invalid_revisions_never_become_zero_flow():
    vs=load()
    row=select(vs,BASKETS["COMMON23"],"2026-11-02","2026-11-03T09:30:00+08:00")
    assert row["net_100m_cny_rounded"] is None
    assert len(row["invalid_members"])==14
    assert not row["eligible_for_exploratory_replay"]
    fixed=select(vs,BASKETS["COMMON23"],"2026-11-02","2026-11-03T10:36:00+08:00")
    assert fixed["numerically_complete"]
    later_bad=select(vs,BASKETS["COMMON23"],"2026-11-02","2026-11-03T10:40:00+08:00")
    assert later_bad["net_100m_cny_rounded"] is None
