"""Append-only-by-filename Git history for each GitHub Actions research run.

Files are uniquely named by GITHUB_RUN_ID. We refuse to replace a previous
record; Git permissions permit administrators to rewrite history, so this is
tamper-evident when reviewed, not cryptographically immutable.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def make_record(output: Path, run_id: str, sha: str, phase: str) -> tuple[Path, dict]:
    if not run_id.isdigit() or len(run_id) > 32:
        raise ValueError("invalid GitHub run id")
    if phase not in {"pre", "mid", "close"}:
        raise ValueError("unknown phase")
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    audit = output / "audit.json"
    if audit.exists():
        payload = audit.read_bytes()
        state = json.loads(payload)
        digest = hashlib.sha256(payload).hexdigest()
    else:
        state = {"status": "FAILED_BEFORE_AUDIT_FILE"}
        digest = None
    signals_file = output / "signals.json"
    signals = json.loads(signals_file.read_text("utf-8")) if signals_file.exists() else None
    trades_file = output / "historical_trades_exploratory.json"
    if trades_file.exists():
        trade_payload = trades_file.read_bytes()
        # Research trades are synthetic execution proxies, NOT actual fills.
        # For current 12-name scope, preserve all underlying replay rows.
        if len(trade_payload) > 2_000_000:
            raise ValueError("trade replay exceeds 2MB; would violate complete archival gate")
        trades_archive = json.loads(trade_payload)
        trades_digest = hashlib.sha256(trade_payload).hexdigest()
    else:
        trades_archive, trades_digest = None, None
    record = {
        "schema_version": 2,
        "github_run_id": run_id,
        "source_commit_sha": sha,
        "collected_beijing_time": now.isoformat(),
        "phase": phase,
        "audit_sha256": digest,
        "historical_trades_sha256": trades_digest,
        "historical_replay": trades_archive,
        "audit": state,
        "signals": signals,
        "record_type": "automated_observation_not_actual_trade",
        "no_real_portfolio_position_implied": True,
    }
    attempt = int(os.getenv("GITHUB_RUN_ATTEMPT", "1"))
    if attempt < 1 or attempt > 1000:
        raise ValueError("invalid run attempt")
    record["github_run_attempt"] = attempt
    dest = Path("records") / now.strftime("%Y-%m-%d") / phase / f"{run_id}-a{attempt}.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        raise FileExistsError(f"never rewrite old run record: {dest}")
    dest.write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str)+"\n", encoding="utf-8")
    return dest, record


if __name__ == "__main__":
    out = Path(os.environ.get("RESEARCH_OUTPUT", "output"))
    dest, record = make_record(
        out, os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_SHA"],
        os.environ.get("RUN_PHASE", "close"),
    )
    print(f"RECORD_CREATED path={dest} status={record['audit'].get('status')} run={record['github_run_id']}")
