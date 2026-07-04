"""Temporary QQQ M1 exporter using GitHub Actions Results artifact protocol.

The historical market data is obtained from the free Dukascopy chart endpoint.
The output ZIP is published only as an artifact of this GitHub Actions run.
"""
from __future__ import annotations

import base64
import hashlib
import importlib.util
import json
import os
import shutil
import zipfile
from pathlib import Path

import pandas as pd
import requests

ARTIFACT_NAME = "qqq-m1-2026-validation-direct"
SERVICE = "github.actions.results.api.v1.ArtifactService"


def _load_core():
    path = Path(__file__).with_name("test_qqq_macro_m1_replay.py")
    spec = importlib.util.spec_from_file_location("qqq_m1_direct_core", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _backend_ids(token: str) -> tuple[str, str]:
    parts = token.split(".")
    if len(parts) < 2:
        raise RuntimeError("invalid ACTIONS_RUNTIME_TOKEN")
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    for scope in str(claims.get("scp", "")).split():
        fields = scope.split(":")
        if len(fields) == 3 and fields[0] == "Actions.Results":
            return fields[1], fields[2]
    raise RuntimeError("Actions.Results scope not found")


def _twirp(results_url: str, token: str, method: str, payload: dict) -> dict:
    origin = results_url.split("/", 3)[:3]
    base = "/".join(origin)
    url = f"{base}/twirp/{SERVICE}/{method}"
    r = requests.post(
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=120,
    )
    print(f"TWIRP_{method}_STATUS", r.status_code)
    if r.status_code >= 400:
        print(f"TWIRP_{method}_BODY", r.text[:2000])
    r.raise_for_status()
    return r.json()


def _publish_artifact(zip_path: Path) -> dict:
    token = os.environ.get("ACTIONS_RUNTIME_TOKEN")
    results_url = os.environ.get("ACTIONS_RESULTS_URL")
    if not token or not results_url:
        raise RuntimeError("GitHub Actions Results runtime variables are missing")
    run_backend_id, job_backend_id = _backend_ids(token)

    create = _twirp(results_url, token, "CreateArtifact", {
        "workflow_run_backend_id": run_backend_id,
        "workflow_job_run_backend_id": job_backend_id,
        "name": ARTIFACT_NAME,
        "version": 7,
        "mime_type": {"value": "application/zip"},
    })
    if not create.get("ok"):
        raise RuntimeError(f"CreateArtifact not ok: {create}")
    signed = create.get("signed_upload_url") or create.get("signedUploadUrl")
    if not signed:
        raise RuntimeError("CreateArtifact missing signed upload URL")

    content = zip_path.read_bytes()
    sha = hashlib.sha256(content).hexdigest()
    put = requests.put(
        signed,
        data=content,
        headers={"x-ms-blob-type": "BlockBlob", "Content-Type": "application/zip"},
        timeout=300,
    )
    print("AZURE_BLOB_PUT_STATUS", put.status_code)
    if put.status_code >= 400:
        print("AZURE_BLOB_PUT_BODY", put.text[:2000])
    put.raise_for_status()

    finalize = _twirp(results_url, token, "FinalizeArtifact", {
        "workflow_run_backend_id": run_backend_id,
        "workflow_job_run_backend_id": job_backend_id,
        "name": ARTIFACT_NAME,
        "size": str(len(content)),
        "hash": {"value": f"sha256:{sha}"},
    })
    if not finalize.get("ok"):
        raise RuntimeError(f"FinalizeArtifact not ok: {finalize}")
    return {"artifact": ARTIFACT_NAME, "artifact_id": finalize.get("artifact_id") or finalize.get("artifactId"), "bytes": len(content), "sha256": sha}


def _write_outputs(core, outdir: Path) -> dict:
    daily = core.fetch_daily()
    start = pd.Timestamp("2026-02-01T00:00:00Z")
    end = pd.Timestamp("2026-06-27T23:59:59Z")
    bid = core.rth(core.duka_fetch("B", start, end))
    ask = core.rth(core.duka_fetch("A", start, end))
    quotes = core.merge_quotes(bid, ask)
    results = [core.simulate_event(daily, quotes, event) for event in core.EVENTS]
    trades = [r for r in results if r.get("status") == "TRADE"]

    equity = 0.0
    peak = 0.0
    max_dd_r = 0.0
    equity_curve = []
    for r in trades:
        equity += float(r["pnl_r"])
        peak = max(peak, equity)
        dd = equity - peak
        max_dd_r = min(max_dd_r, dd)
        equity_curve.append({"event": r["event"], "d0": r["d0"], "pnl_r": r["pnl_r"], "equity_r": equity, "drawdown_r": dd})

    summary = {
        "data_source": "Dukascopy freeserv chart/json3 QQQ.US/USD 1MIN BID and ASK",
        "execution_model": "buy triggers/exits on ASK/BID; sell triggers/exits on BID/ASK; RTH only",
        "rules": "0.20 ATR20 Wilder buffer; OCO D+1 only; stop 2 ATR; take 2R; 7 sessions; Macro Shield",
        "events": len(results),
        "trades": len(trades),
        "wins": sum(float(r["pnl_r"]) > 0 for r in trades),
        "losses": sum(float(r["pnl_r"]) < 0 for r in trades),
        "sum_r": sum(float(r["pnl_r"]) for r in trades),
        "sum_trade_pct": sum(float(r["pnl_pct"]) for r in trades),
        "compound_notional_pct": (pd.Series([1 + float(r["pnl_pct"]) / 100 for r in trades]).prod() - 1) * 100 if trades else 0.0,
        "max_closed_equity_dd_r": max_dd_r,
        "worst_mae_pct": min((float(r["mae_pct"]) for r in trades), default=0.0),
        "statuses": pd.Series([r["status"] for r in results]).value_counts().to_dict(),
        "exit_reasons": pd.Series([r["exit_reason"] for r in trades]).value_counts().to_dict(),
        "quote_rows": len(quotes),
        "quote_days": int(quotes["date_et"].nunique()),
        "quote_first": str(quotes["timestamp"].min()),
        "quote_last": str(quotes["timestamp"].max()),
        "daily_crosscheck": core.compare_daily(daily, quotes),
    }

    bid.to_csv(outdir / "qqq_dukascopy_bid_m1_rth.csv.gz", index=False, compression="gzip")
    ask.to_csv(outdir / "qqq_dukascopy_ask_m1_rth.csv.gz", index=False, compression="gzip")
    quotes.to_csv(outdir / "qqq_dukascopy_bidask_m1_rth.csv.gz", index=False, compression="gzip")
    daily.to_csv(outdir / "qqq_daily_wilder_atr20.csv", index=False)
    (outdir / "event_results.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    (outdir / "strategy_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (outdir / "equity_curve_r.json").write_text(json.dumps(equity_curve, indent=2, default=str), encoding="utf-8")
    return summary


def test_qqq_m1_direct_artifact_export():
    core = _load_core()
    outdir = Path("/tmp/qqq_m1_direct")
    if outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True)
    summary = _write_outputs(core, outdir)
    zip_path = Path("/tmp/qqq_m1_2026_validation_direct.zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted(outdir.iterdir()):
            zf.write(path, arcname=path.name)
    published = _publish_artifact(zip_path)
    print("QQQ_DIRECT_SUMMARY", json.dumps(summary, sort_keys=True, default=str))
    print("QQQ_DIRECT_ARTIFACT", json.dumps(published, sort_keys=True))
