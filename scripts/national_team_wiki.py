"""Generate a concise MOC view from actual national-team saved source records.

Never updates raw JSON or manually curated experiment / failure logs. A new
source attempt (possibly failed) is separated from the latest genuinely
completed four-ETF research factor and the latest usable watchlist.
"""
from __future__ import annotations
import json,os
from pathlib import Path
from datetime import datetime

CATEGORIES={
    "national_team_etf":"ETF source attempts",
    "national_team_merged":"Four-fund merged funding",
    "national_team_watch":"CSI300 stock research watches",
    "national_team_pcf":"Official exchange PCF attempts",
    "national_team_events":"Frozen paper-event cohorts",
    "national_team_paper":"Matured paper outcomes",
    "national_team_audits":"Independent research integrity audit",
    "national_team_strategy":"Prospective four-ETF V2 stock cohorts",
}

def enumerate_records(root:Path)->list[tuple[str,Path,dict]]:
    found=[]
    for folder in CATEGORIES:
        for path in (root/"records"/folder).glob("*/*.json"):
            try:
                r=json.loads(path.read_text(encoding="utf-8"))
            except (ValueError,OSError):
                raise ValueError(f"unreadable source evidence JSON: {path}") from None
            if not isinstance(r,dict):
                raise ValueError(f"record is not a dict: {path}")
            found.append((folder,path,r))
    found.sort(key=lambda x:(x[1].parent.name,str(x[2].get("run_id") or ""),
                             x[1].name),reverse=True)
    return found

def last_for(records:list[tuple[str,Path,dict]],folder:str,predicate=None):
    for entry in records:
        if entry[0]==folder and (predicate is None or predicate(entry[2])):
            return entry
    return None

def relative_link(path:Path,reference_dir:Path)->str:
    return Path(os.path.relpath(path,reference_dir)).as_posix()

def generate(root:Path,*,now:str, records:list[tuple[str,Path,dict]]|None=None)->dict:
    if records is None:records=enumerate_records(root)
    wiki=root/"wiki"
    (wiki/"indices").mkdir(parents=True,exist_ok=True)
    (wiki/"compiled").mkdir(parents=True,exist_ok=True)
    index=wiki/"indices"/"national-team.md"
    briefing=wiki/"compiled"/"briefing.md"
    def marker(ident,kind,header):
        return f"---\nid: {ident}\ntype: {kind}\nstatus: maintained\nupdated: {now[:10]}\n---\n# {header}\n\n"
    lead=("Source-backed **captured observations**, not broker fills. "
          "Latest failed attempt does NOT invalidate prior historic source evidence; "
          "prior positive data is not a newly observed today's inflow.\n\n"
          "[根MOC](../../MOC.md) · [E2E红队审计](../audits/AUD-2026-10-28-e2e-release-gate.md)\n\n")
    lines=["| Source class | Trade/record date | Run ID | Recorded status | Evidence |",
           "| --- | --- | --- | --- | --- |"]
    for folder,path,r in records:
        name=CATEGORIES[folder]
        date=str(r.get("funding_date") or r.get("asof_requested") or
                 r.get("asof") or path.parent.name)
        run=str(r.get("run_id") or path.stem)
        status=str(r.get("status") or
                   (r.get("funding_event") or {}).get("status") or "UNVERIFIED")
        label=relative_link(path,index.parent)
        lines.append(f"| {name} | {date} | {run} | {status.replace('|','/')} | [JSON]({label}) |")
    if not records:lines.append("| No national-team source record | — | — | unavailable | — |")
    index.write_text(marker("GENERATED-NATIONAL-TEAM","log","国家队四ETF与股票追踪实际运行索引")
                     +lead+"\n".join(lines)+"\n",encoding="utf-8")
    attempt=last_for(records,"national_team_etf")
    full=last_for(records,"national_team_merged",
        lambda r:(r.get("funding_event") or {}).get("four_etf_factor") is not None)
    # The original successfully observed direct 4-fund factor may predate merge.
    if full is None:
        full=last_for(records,"national_team_etf",
            lambda r:(r.get("funding_event") or {}).get("four_etf_factor") is not None)
    watch=last_for(records,"national_team_watch",
                   lambda r:r.get("status")=="INDEX_PROXY_RESEARCH_WATCHLIST")
    frozen=last_for(records,"national_team_events")
    paper=last_for(records,"national_team_paper")
    pcf=last_for(records,"national_team_pcf")
    red=last_for(records,"national_team_audits")
    v2=last_for(records,"national_team_strategy",lambda r:r.get("model_version")=="NT_FLOW_PIT_V2_20261028" and r.get("status")=="FROZEN_PROSPECTIVE_RESEARCH" and r.get("new_event_count",0)>0)
    info=[
        "[根MOC](../../MOC.md) · [国家队所有实跑记录](../indices/national-team.md) · "
        "[模型演进](../models/registry.md) · [红队审计](../audits/AUD-2026-10-28-e2e-release-gate.md)",
        "",
        "**主线：中央汇金等法定主体披露（低频） × 固定四沪深300ETF资金份额（高频） → 指数/PCF对应股票 → S0 ETF基准 vs S1/S2选股组合。**",
        "",
    ]
    def bullet(label,entry):
        if entry is None:return f"- {label}：无可复核持久化记录。"
        folder,path,r=entry
        return (f"- {label}：[run {r.get('run_id',path.stem)}]({relative_link(path,briefing.parent)})；"
                f"状态 `{r.get('status','UNVERIFIED')}`；"
                f"日期 {r.get('funding_date') or r.get('asof_requested') or r.get('asof') or path.parent.name}。")
    info.append(bullet("最新ETF源采集尝试",attempt))
    info.append(bullet("最近可完整核验四ETF份额/NAV的历史记录",full))
    if full is not None:
        _,path,r=full
        ev=r.get("funding_event") or {}
        fact=ev.get("four_etf_factor") or {}
        if fact:
            info.extend([
                f"- 最近完整基金资金研究日：**{fact.get('trade_date')}**；"
                f"合计当日净份额×NAV代理 **{fact.get('daily_net_creation_proxy_cny')} 元**；"
                "这不是汇金个人账户当日买入。",
                f"- 最近完整5日资金强度：**{(fact.get('five_day') or {}).get('net_creation_pct_initial_aum')}**；"
                "基金NAV尚需发行人原件复核、份额拆并需独立验证；极值应标异常而非直接买点。"
            ])
    info.append(bullet("最近真实指数权重代理股票观察名单",watch))
    if watch is not None:
        _,path,r=watch
        ranking=r.get("research_ranking") or {}
        info.append(f"- 最新实测股票样本数：**{ranking.get('ranked_from_n_stocks','未知')}**；"
                    f"指数权重覆盖约 **{r.get('pool_weight_coverage','未知')}**；"
                    "指数权重非ETF真实PCF，且未证明个股跟随收益。")
    info.append(bullet("最近四ETF独立V2前瞻选股",v2))
    if v2 is not None:
        _,v2_path,v2_record=v2
        s1=[x["symbol"] for x in v2_record.get("s1_ranked",[])]
        s2=[x["symbol"] for x in v2_record.get("s2_ranked",[])]
        info.append(f"- V2真实首次可得时刻：{v2_record.get('strategy_first_public_at')}，底层四ETF资金日：{v2_record.get('flow_date')}；"
                    f"S1资金/成交额研究组 **{', '.join(s1)}**；"
                    f"S2独立价格确认研究组 **{', '.join(s2)}**。")
        info.append("- V2仅以资金为择时触发（CSI300代理权重跨ETF相同，不能辨识逐股票实际买盘）；"
                    "5/10/20日净超额收益待未来真实行情成熟；旧V1组合不可替换初始冻结股单。")
    for label,item in [
        ("最近PCF采集尝试",pcf),("最近纸面事件冻结",frozen),
        ("最近纸面收益观察",paper),("最近独立实跑红队审计",red)]:
        info.append(bullet(label,item))
    info.extend(["", "**投资结果状态：暂无独立样本外净超额收益验证；不推断任何国家队真实账户买卖、已成交订单或必然盈利。**",
                "", "自动页面仅汇总已保存的证据。最新综合workflow是否为绿色，仍需单独查GitHub Actions对应SHA。"])
    briefing.write_text(marker("COMPILED-BRIEFING","overview","国家队资金→成分股研究 Agent 最新证据简报")
                        +"\n".join(info)+"\n",encoding="utf-8")
    return {"national_team_records":len(records),"sources_index":str(index),
            "briefing":str(briefing),"last_complete_four_run":full[2].get("run_id") if full else None}
