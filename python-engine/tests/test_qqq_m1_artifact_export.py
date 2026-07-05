"""Temporary exporter for the QQQ M1 research run.

It reuses the direct public-source replay module, writes the raw BID/ASK M1
bars and compact replay outputs to /tmp, then invokes GitHub's official
upload-artifact v4 bundled action inside the already-running Actions job.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pandas as pd
import requests


def _load_core():
    path = Path(__file__).with_name("test_qqq_macro_m1_replay.py")
    spec = importlib.util.spec_from_file_location("qqq_macro_m1_core", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _upload_artifact(outdir: Path) -> None:
    js_url = "https://raw.githubusercontent.com/actions/upload-artifact/v4/dist/upload/index.js"
    r = requests.get(js_url, timeout=120)
    r.raise_for_status()
    js = Path("/tmp/upload-artifact-v4.js")
    js.write_bytes(r.content)
    env = os.environ.copy()
    env.update({
        "INPUT_NAME": "qqq-m1-2026-macro-validation",
        "INPUT_PATH": str(outdir),
        "INPUT_IF-NO-FILES-FOUND": "error",
        "INPUT_RETENTION-DAYS": "30",
        "INPUT_COMPRESSION-LEVEL": "6",
        "INPUT_OVERWRITE": "true",
        "INPUT_INCLUDE-HIDDEN-FILES": "false",
    })
    proc = subprocess.run(["node", str(js)], env=env, text=True, capture_output=True, timeout=300)
    print("ARTIFACT_UPLOAD_STDOUT", proc.stdout[-4000:])
    print("ARTIFACT_UPLOAD_STDERR", proc.stderr[-4000:])
    if proc.returncode != 0:
        raise RuntimeError(f"upload-artifact returned {proc.returncode}")


def test_export_qqq_m1_artifact():
    core = _load_core()
    outdir = Path("/tmp/qqq_m1_validation")
    outdir.mkdir(parents=True, exist_ok=True)

    daily = core.fetch_daily()
    start = pd.Timestamp("2026-02-01T00:00:00Z")
    end = pd.Timestamp("2026-06-27T23:59:59Z")
    bid = core.rth(core.duka_fetch("B", start, end))
    ask = core.rth(core.duka_fetch("A", start, end))
    quotes = core.merge_quotes(bid, ask)

    results = [core.simulate_event(daily, quotes, e) for e in core.EVENTS]
    trades = [x for x in results if x.get("status") == "TRADE"]
    equity = 0.0
    peak = 0.0
    max_dd_r = 0.0
    equity_curve = []
    for trade in trades:
        equity += float(trade["pnl_r"])
        peak = max(peak, equity)
        max_dd_r = min(max_dd_r, equity - peak)
        equity_curve.append({"d0": trade["d0"], "event": trade["event"], "pnl_r": trade["pnl_r"], "equity_r": equity, "drawdown_r": equity - peak})

    summary = {
        "source": "Dukascopy free chart endpoint; QQQ.US/USD; BID+ASK; 1MIN; RTH 09:30-16:00 America/New_York",
        "rules": "0.20 ATR20 Wilder buffer / OCO D+1 only / executable quote model / stop 2 ATR / take 2R / 7 sessions / Macro Shield",
        "events": len(results),
        "trades": len(trades),
        "wins": sum(float(x["pnl_r"]) > 0 for x in trades),
        "losses": sum(float(x["pnl_r"]) < 0 for x in trades),
        "sum_r": sum(float(x["pnl_r"]) for x in trades),
        "sum_trade_pct": sum(float(x["pnl_pct"]) for x in trades),
        "compound_notional_pct": (pd.Series([1 + float(x["pnl_pct"]) / 100 for x in trades]).prod() - 1) * 100 if trades else 0.0,
        "max_closed_equity_dd_r": max_dd_r,
        "worst_mae_pct": min((float(x["mae_pct"]) for x in trades), default=0.0),
        "statuses": pd.Series([x["status"] for x in results]).value_counts().to_dict(),
        "exit_reasons": pd.Series([x["exit_reason"] for x in trades]).value_counts().to_dict(),
        "quote_rows": len(quotes),
        "quote_days": int(quotes["date_et"].nunique()),
        "quote_first": str(quotes["timestamp"].min()),
        "quote_last": str(quotes["timestamp"].max()),
        "daily_crosscheck": core.compare_daily(daily, quotes),
    }

    # Raw/source files and compact audit outputs.
    bid.to_csv(outdir / "qqq_dukascopy_bid_m1_rth.csv.gz", index=False, compression="gzip")
    ask.to_csv(outdir / "qqq_dukascopy_ask_m1_rth.csv.gz", index=False, compression="gzip")
    quotes.to_csv(outdir / "qqq_dukascopy_bidask_m1_rth.csv.gz", index=False, compression="gzip")
    daily.to_csv(outdir / "qqq_daily_reference_with_wilder_atr20.csv", index=False)
    (outdir / "event_results.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    (outdir / "strategy_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    (outdir / "equity_curve_r.json").write_text(json.dumps(equity_curve, indent=2, default=str), encoding="utf-8")

    # Yahoo June overlap bars, when Yahoo still exposes the requested 1m window.
    yahoo_status = {"status": "not_attempted"}
    try:
        import yfinance as yf
        y = yf.download("QQQ", start="2026-06-05", end="2026-06-27", interval="1m", auto_adjust=False, prepost=False, progress=False, threads=False)
        if y is not None and not y.empty:
            if isinstance(y.columns, pd.MultiIndex):
                y.columns = y.columns.get_level_values(0)
            y = y.reset_index()
            y.to_csv(outdir / "qqq_yahoo_m1_june_overlap.csv.gz", index=False, compression="gzip")
            yahoo_status = {"status": "ok", "rows": len(y), "first": str(y.iloc[0, 0]), "last": str(y.iloc[-1, 0])}
        else:
            yahoo_status = {"status": "empty"}
    except Exception as exc:
        yahoo_status = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
    (outdir / "yahoo_overlap_status.json").write_text(json.dumps(yahoo_status, indent=2), encoding="utf-8")

    files = []
    for path in sorted(outdir.iterdir()):
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": _sha256(path)})
    manifest = {"summary": summary, "yahoo": yahoo_status, "files": files}
    (outdir / "manifest.json").write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    print("QQQ_ARTIFACT_SUMMARY", json.dumps(summary, sort_keys=True, default=str))
    print("QQQ_ARTIFACT_MANIFEST", json.dumps(files, sort_keys=True))
    print("QQQ_YAHOO_STATUS", json.dumps(yahoo_status, sort_keys=True))
    _upload_artifact(outdir)
