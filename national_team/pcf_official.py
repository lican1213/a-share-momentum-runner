"""Archive official SSE ETF latest PCF publication for core Shanghai funds.

Only a parsed dated exchange filing counts as verified PCF. Never assign
a missing publication date or treat an index-weight file as ETF PCF.
"""
from __future__ import annotations
import argparse,hashlib,json,os,re
from datetime import datetime
from io import StringIO
from pathlib import Path
from zoneinfo import ZoneInfo

PCF_BASE="https://www.sse.com.cn/disclosure/fund/etflist/detail.shtml"
CODES=("510300","510310","510330")
EXCHANGE="https://www.sse.com.cn/disclosure/fund/etflist/"

def parse_official_html(html:str,code:str,first_observed:str)->dict:
    """Parse source HTML tables *only* when actual dated data is in response."""
    import pandas as pd
    from bs4 import BeautifulSoup
    soup=BeautifulSoup(html,"html.parser")
    text=soup.get_text(" ",strip=True)
    match=re.search(r"最新公告日期\s*[:：]?\s*(20\d{2}[-/]\d{1,2}[-/]\d{1,2})",text)
    if not match:
        return {"status":"NO_DATED_OFFICIAL_PCF_IN_HTTP_RESPONSE",
                "code":code,"first_observed_at":first_observed}
    day=match.group(1).replace("/","-")
    from datetime import date
    if date.fromisoformat(day)>date.fromisoformat(first_observed[:10]):
        raise ValueError("PCF date after capture day")
    identity=re.search(r"基金代码\s*[:：]?\s*(\d{6})",text)
    if identity and identity.group(1)!=code:
        raise ValueError("PCF fund identity does not match request")
    tables=pd.read_html(StringIO(html))
    components=[]
    for table in tables:
        table.columns=[str(x).replace("\n","").replace(" ","") for x in table.columns]
        symbol=next((col for col in table.columns if "证券代码" in col),None)
        quantity=next((col for col in table.columns if "股票数量" in col or "成份股数量" in col),None)
        if symbol is None or quantity is None:continue
        flag=next((col for col in table.columns if "现金替代标志" in col),None)
        for _,row in table.iterrows():
            symbol_code=str(row[symbol]).split(".")[0].zfill(6)
            if len(symbol_code)!=6 or not symbol_code.isdigit():
                continue
            value=str(row[quantity]).replace(",","").strip()
            try:
                shares=int(float(value))
            except (ValueError,OverflowError):
                continue
            if shares<0:raise ValueError("negative PCF component shares")
            components.append({"symbol":symbol_code,"basket_shares_per_creation_unit":shares,
                               "cash_substitution":str(row[flag]) if flag else "UNKNOWN"})
    if len(components)<100:
        return {"status":"DATED_PCF_BUT_CONSTITUENTS_NOT_IN_STATIC_RESPONSE",
                "code":code,"pcf_date":day,"parsed_components":len(components),
                "first_observed_at":first_observed}
    if len(set(x["symbol"] for x in components))!=len(components):
        raise ValueError("duplicate PCF security symbol")
    return {"status":"OFFICIAL_DATED_PCF_COMPONENTS_CAPTURED","code":code,
            "pcf_date":day,"first_observed_at":first_observed,
            "source_url":PCF_BASE+f"?etfClass=03&fundid={code}&type=008",
            "component_count":len(components),"components":components,
            "component_stock_values_and_PCF_weights_not_yet_verified":True}

def collect(out_root:Path,run_id:str,attempt:str,*,getter=None)->tuple[Path,dict]:
    import requests
    now=datetime.now(ZoneInfo("Asia/Shanghai"))
    out={"status":"ATTEMPTED","run_id":run_id,"attempt":attempt,"captured_at":now.isoformat(),
         "exchange_url":EXCHANGE,"sources":{},"errors":[],
         "source_kind":"ORIGINAL_EXCHANGE_HTTP_PCF_NOT_INDEX_WEIGHTS"}
    if getter is None:
        def getter(url,params):
            res=requests.get(url,params=params,headers={"Referer":"https://www.sse.com.cn/",
                              "User-Agent":"Mozilla/5.0"},timeout=18)
            res.raise_for_status()
            return res.text
    for code in CODES:
        params={"etfClass":"03","fundid":code,"type":"008"}
        try:
            html=getter(PCF_BASE,params)
            item=parse_official_html(html,code,datetime.now(ZoneInfo("Asia/Shanghai")).isoformat())
            item["http_response_sha256"]=hashlib.sha256(html.encode()).hexdigest()
            out["sources"][code]=item
        except Exception as exc:
            out["errors"].append(f"{code}:{type(exc).__name__}:{str(exc)[:200]}")
    good=sum(v.get("status")=="OFFICIAL_DATED_PCF_COMPONENTS_CAPTURED" for v in out["sources"].values())
    out["status"]="SSE_DATED_PCF_CAPTURED" if good else "SSE_PCF_FETCHED_BUT_NOT_VERIFIED"
    out["usable_pcf_count"]=good
    target=out_root/now.date().isoformat()/f"{run_id}-a{attempt}.json"
    if target.exists():raise FileExistsError("never overwrite previous PCF evidence")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return target,out

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default="records/national_team_pcf")
    args=parser.parse_args()
    target,out=collect(Path(args.out),os.environ.get("GITHUB_RUN_ID","local"),
                       os.environ.get("GITHUB_RUN_ATTEMPT","1"))
    print(json.dumps({"status":out["status"],"usable":out["usable_pcf_count"],
                      "errors":len(out["errors"]),"record":str(target)},ensure_ascii=False))

if __name__=="__main__":
    main()
