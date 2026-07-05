"""Temporary QQQ Macro Reset M1 execution-validation study.

The test fetches:
- QQQ daily OHLC from a public versioned GitHub CSV.
- QQQ.US/USD 1-minute BID and ASK bars from Dukascopy's free chart endpoint.
- Yahoo Finance QQQ 1-minute bars for the June 2026 overlap window when available.

It replays the frozen rules and intentionally fails at the end so pytest prints
all JSON results into the GitHub Actions log for remote audit.
"""
from __future__ import annotations

import io
import json
import random
import string
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

import pandas as pd
import requests

NY = ZoneInfo("America/New_York")
DUKA_URL = "https://freeserv.dukascopy.com/2.0/index.php"
DUKA_INSTRUMENT = "QQQ.US/USD"
DAILY_URL = "https://raw.githubusercontent.com/xunme1/stock_ranking/30bca2c5889b4d1c845b8228b41ef2947bc4a46d/data/raw/daily/QQQ.csv"

EVENTS = [
    {"event":"CPI","d0":"2026-02-13","next_macro":"2026-02-20"},
    {"event":"GDP","d0":"2026-02-20","next_macro":"2026-03-11"},
    {"event":"CPI","d0":"2026-03-11","next_macro":"2026-03-18"},
    {"event":"FOMC","d0":"2026-03-18","next_macro":"2026-04-10"},
    {"event":"CPI","d0":"2026-04-10","next_macro":"2026-04-29"},
    {"event":"FOMC","d0":"2026-04-29","next_macro":"2026-04-30"},
    {"event":"GDP","d0":"2026-04-30","next_macro":"2026-05-12"},
    {"event":"CPI","d0":"2026-05-12","next_macro":"2026-06-10"},
    {"event":"CPI","d0":"2026-06-10","next_macro":"2026-06-17"},
    {"event":"FOMC","d0":"2026-06-17","next_macro":None},
]


def emit(tag: str, obj) -> None:
    print(tag + " " + json.dumps(obj, sort_keys=True, default=str))


def fetch_daily() -> pd.DataFrame:
    r = requests.get(DAILY_URL, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    cols = {str(c).lower(): c for c in df.columns}
    date_col = cols.get("date") or cols.get("timestamp") or cols.get("datetime")
    if date_col is None:
        date_col = df.columns[0]
    rename = {date_col: "date"}
    for name in ("open", "high", "low", "close", "volume"):
        if name in cols:
            rename[cols[name]] = name
    df = df.rename(columns=rename)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.tz_localize(None)
    for c in ("open", "high", "low", "close"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["date", "open", "high", "low", "close"]).sort_values("date").reset_index(drop=True)

    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    # Wilder ATR20: seed with first 20-TR arithmetic mean, then recursive smoothing.
    atr = pd.Series(index=df.index, dtype=float)
    if len(df) >= 20:
        atr.iloc[19] = tr.iloc[:20].mean()
        for i in range(20, len(df)):
            atr.iloc[i] = ((atr.iloc[i-1] * 19) + tr.iloc[i]) / 20
    df["atr20_wilder"] = atr
    return df


def trading_days_after(daily: pd.DataFrame, d0: str) -> list[pd.Timestamp]:
    d = pd.Timestamp(d0)
    return daily.loc[daily["date"] > d, "date"].tolist()


def duka_fetch(side: str, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    cursor = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    rows = []
    retries = 0
    first = True
    loops = 0
    while True:
        loops += 1
        if loops > 50:
            raise RuntimeError("Dukascopy paging loop exceeded 50")
        chars = string.ascii_letters + string.digits
        jsonp = "_callbacks____" + "".join(random.choices(chars, k=9))
        params = {
            "path": "chart/json3",
            "splits": "true",
            "stocks": "true",
            "time_direction": "N",
            "jsonp": jsonp,
            "last_update": str(cursor),
            "offer_side": side,
            "instrument": DUKA_INSTRUMENT,
            "interval": "1MIN",
            "limit": "30000",
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135 Safari/537.36",
            "Referer": "https://freeserv.dukascopy.com/2.0/?path=chart/index",
        }
        try:
            r = requests.get(DUKA_URL, params=params, headers=headers, timeout=120)
            r.raise_for_status()
            text = r.text
            prefix = jsonp + "("
            suffix = ");"
            if not (text.startswith(prefix) and text.endswith(suffix)):
                raise RuntimeError(f"unexpected Dukascopy response prefix={text[:120]!r}")
            batch = json.loads(text[len(prefix):-len(suffix)])
            if not first and batch and batch[0][0] == cursor:
                batch = batch[1:]
            if not batch:
                break
            for row in batch:
                if row[0] > end_ms:
                    batch = []
                    break
                rows.append(row)
                cursor = int(row[0])
            if not batch or cursor >= end_ms:
                break
            first = False
            retries = 0
        except Exception:
            retries += 1
            if retries > 5:
                raise
    df = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "close", "volume"])
    if df.empty:
        return df
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
    df["side"] = side
    return df.sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)


def rth(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    x = df.copy()
    et = x["timestamp"].dt.tz_convert(NY)
    t = et.dt.time
    keep = (et.dt.weekday < 5) & (t >= dtime(9, 30)) & (t < dtime(16, 0))
    x = x.loc[keep].copy()
    x["timestamp_et"] = et.loc[keep]
    x["date_et"] = x["timestamp_et"].dt.tz_localize(None).dt.normalize()
    return x.reset_index(drop=True)


def merge_quotes(bid: pd.DataFrame, ask: pd.DataFrame) -> pd.DataFrame:
    b = bid.rename(columns={c: f"bid_{c}" for c in ("open", "high", "low", "close", "volume")})
    a = ask.rename(columns={c: f"ask_{c}" for c in ("open", "high", "low", "close", "volume")})
    q = pd.merge(b.drop(columns=["side"], errors="ignore"), a.drop(columns=["side"], errors="ignore"), on="timestamp", how="inner")
    q["timestamp_et"] = q["timestamp"].dt.tz_convert(NY)
    q["date_et"] = q["timestamp_et"].dt.tz_localize(None).dt.normalize()
    return q.sort_values("timestamp").reset_index(drop=True)


def simulate_event(daily: pd.DataFrame, q: pd.DataFrame, event: dict) -> dict:
    d0 = pd.Timestamp(event["d0"])
    row = daily.loc[daily["date"] == d0]
    if row.empty:
        return {**event, "status":"ERROR_D0_MISSING"}
    row = row.iloc[0]
    atr = float(row["atr20_wilder"])
    eh = float(row["high"])
    el = float(row["low"])
    buy = eh + 0.20 * atr
    sell = el - 0.20 * atr

    future_days = trading_days_after(daily, event["d0"])
    if not future_days:
        return {**event, "status":"ERROR_NO_FUTURE_DAY"}
    d1 = future_days[0]
    next_macro = pd.Timestamp(event["next_macro"]) if event.get("next_macro") else None
    if next_macro is not None and d1 == next_macro:
        return {**event, "status":"NO_TRADE_NEXT_MACRO_D1", "d1":str(d1.date()), "eh":eh, "el":el, "atr20":atr, "buy_stop":buy, "sell_stop":sell}

    day = q[q["date_et"] == d1].copy()
    if day.empty:
        return {**event, "status":"ERROR_D1_M1_MISSING", "d1":str(d1.date()), "buy_stop":buy, "sell_stop":sell}

    entry = None
    ambiguous = None
    for _, bar in day.iterrows():
        # executable quote model: buy trigger on ASK, sell trigger on BID
        buy_gap = bar["ask_open"] >= buy
        sell_gap = bar["bid_open"] <= sell
        buy_hit = bar["ask_high"] >= buy
        sell_hit = bar["bid_low"] <= sell
        if buy_gap and sell_gap:
            ambiguous = "BOTH_GAP_IMPOSSIBLE_OR_BAD_QUOTES"
            break
        if buy_gap:
            entry = {"direction":"LONG", "entry":float(bar["ask_open"]), "trigger_minute":bar["timestamp_et"], "fill":"GAP_OPEN"}
            break
        if sell_gap:
            entry = {"direction":"SHORT", "entry":float(bar["bid_open"]), "trigger_minute":bar["timestamp_et"], "fill":"GAP_OPEN"}
            break
        if buy_hit and sell_hit:
            ambiguous = "BOTH_OCO_SIDES_TOUCHED_SAME_M1"
            break
        if buy_hit:
            entry = {"direction":"LONG", "entry":buy, "trigger_minute":bar["timestamp_et"], "fill":"TRIGGER"}
            break
        if sell_hit:
            entry = {"direction":"SHORT", "entry":sell, "trigger_minute":bar["timestamp_et"], "fill":"TRIGGER"}
            break

    base = {**event, "d1":str(d1.date()), "eh":eh, "el":el, "atr20":atr, "buy_stop":buy, "sell_stop":sell}
    if ambiguous:
        return {**base, "status":"AMBIGUOUS_M1", "ambiguity":ambiguous}
    if entry is None:
        return {**base, "status":"NO_TRIGGER_D1"}

    direction = entry["direction"]
    ep = float(entry["entry"])
    risk = 2.0 * atr
    if direction == "LONG":
        stop = ep - risk
        take = ep + 2.0 * risk
    else:
        stop = ep + risk
        take = ep - 2.0 * risk

    # Trade expiry is close of the 7th trading session, unless Macro Shield exits earlier.
    entry_idx = future_days.index(d1)
    seven_day = future_days[entry_idx + 6] if len(future_days) > entry_idx + 6 else future_days[-1]
    force_day = seven_day
    force_reason = "TIME_STOP"
    if next_macro is not None:
        prior = daily.loc[daily["date"] < next_macro, "date"]
        if not prior.empty:
            macro_exit = prior.iloc[-1]
            if macro_exit < force_day:
                force_day = macro_exit
                force_reason = "MACRO_SHIELD"

    scan = q[(q["timestamp"] >= pd.Timestamp(entry["trigger_minute"]).tz_convert("UTC")) & (q["date_et"] <= force_day)].copy()
    exit_price = None
    exit_time = None
    exit_reason = None
    mae_pct = 0.0
    mfe_pct = 0.0
    same_bar_conflicts = 0

    for _, bar in scan.iterrows():
        if direction == "LONG":
            adverse = (float(bar["bid_low"]) - ep) / ep * 100
            favorable = (float(bar["bid_high"]) - ep) / ep * 100
            mae_pct = min(mae_pct, adverse)
            mfe_pct = max(mfe_pct, favorable)
            stop_hit = float(bar["bid_low"]) <= stop
            take_hit = float(bar["bid_high"]) >= take
            if stop_hit and take_hit:
                same_bar_conflicts += 1
                exit_price, exit_time, exit_reason = stop, bar["timestamp_et"], "STOP_SAME_M1_CONSERVATIVE"
                break
            if stop_hit:
                exit_price, exit_time, exit_reason = stop, bar["timestamp_et"], "STOP"
                break
            if take_hit:
                exit_price, exit_time, exit_reason = take, bar["timestamp_et"], "TAKE"
                break
        else:
            adverse = (ep - float(bar["ask_high"])) / ep * 100
            favorable = (ep - float(bar["ask_low"])) / ep * 100
            mae_pct = min(mae_pct, adverse)
            mfe_pct = max(mfe_pct, favorable)
            stop_hit = float(bar["ask_high"]) >= stop
            take_hit = float(bar["ask_low"]) <= take
            if stop_hit and take_hit:
                same_bar_conflicts += 1
                exit_price, exit_time, exit_reason = stop, bar["timestamp_et"], "STOP_SAME_M1_CONSERVATIVE"
                break
            if stop_hit:
                exit_price, exit_time, exit_reason = stop, bar["timestamp_et"], "STOP"
                break
            if take_hit:
                exit_price, exit_time, exit_reason = take, bar["timestamp_et"], "TAKE"
                break

    if exit_price is None:
        last = scan[scan["date_et"] == force_day].tail(1)
        if last.empty:
            return {**base, **entry, "status":"ERROR_FORCE_EXIT_M1_MISSING", "force_day":str(force_day.date())}
        bar = last.iloc[0]
        exit_price = float(bar["bid_close"] if direction == "LONG" else bar["ask_close"])
        exit_time = bar["timestamp_et"]
        exit_reason = force_reason

    pnl_pct = ((exit_price - ep) / ep * 100) if direction == "LONG" else ((ep - exit_price) / ep * 100)
    pnl_r = ((exit_price - ep) / risk) if direction == "LONG" else ((ep - exit_price) / risk)
    return {
        **base,
        "status":"TRADE",
        **entry,
        "stop":stop,
        "take":take,
        "force_day":str(force_day.date()),
        "exit":float(exit_price),
        "exit_minute":exit_time,
        "exit_reason":exit_reason,
        "pnl_pct":float(pnl_pct),
        "pnl_r":float(pnl_r),
        "mae_pct":float(mae_pct),
        "mfe_pct":float(mfe_pct),
        "same_bar_conflicts":same_bar_conflicts,
    }


def aggregate_rth(q: pd.DataFrame) -> pd.DataFrame:
    mid = q.copy()
    for c in ("open", "high", "low", "close"):
        mid[f"mid_{c}"] = (mid[f"bid_{c}"] + mid[f"ask_{c}"]) / 2.0
    return mid.groupby("date_et").agg(open=("mid_open","first"), high=("mid_high","max"), low=("mid_low","min"), close=("mid_close","last"), bars=("timestamp","size")).reset_index()


def compare_daily(daily: pd.DataFrame, q: pd.DataFrame) -> dict:
    agg = aggregate_rth(q)
    ref = daily[["date","open","high","low","close"]].copy()
    x = pd.merge(agg, ref, left_on="date_et", right_on="date", suffixes=("_duka","_qqq"))
    for c in ("open","high","low","close"):
        x[f"{c}_diff"] = x[f"{c}_duka"] - x[f"{c}_qqq"]
        x[f"{c}_abs_diff"] = x[f"{c}_diff"].abs()
    return {
        "matched_days":int(len(x)),
        "bars_per_day_min":int(x["bars"].min()) if len(x) else None,
        "bars_per_day_median":float(x["bars"].median()) if len(x) else None,
        "median_abs_diff":{c:float(x[f"{c}_abs_diff"].median()) for c in ("open","high","low","close")} if len(x) else {},
        "max_abs_diff":{c:float(x[f"{c}_abs_diff"].max()) for c in ("open","high","low","close")} if len(x) else {},
        "sample_june18":x[x["date"] == pd.Timestamp("2026-06-18")].to_dict("records"),
    }


def yahoo_june_replay(daily: pd.DataFrame, duka_results: list[dict]) -> dict:
    import yfinance as yf
    try:
        df = yf.download("QQQ", start="2026-06-05", end="2026-06-27", interval="1m", auto_adjust=False, prepost=False, progress=False, threads=False)
    except Exception as exc:
        return {"status":"ERROR", "error":f"{type(exc).__name__}: {exc}"}
    if df is None or df.empty:
        return {"status":"NO_DATA"}
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.reset_index().rename(columns={df.reset_index().columns[0]:"timestamp", "Open":"open", "High":"high", "Low":"low", "Close":"close", "Volume":"volume"})
    # Defensive rename because reset_index column naming varies by yfinance version.
    if "timestamp" not in df.columns:
        df = df.rename(columns={df.columns[0]:"timestamp"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    et = df["timestamp"].dt.tz_convert(NY)
    df["timestamp_et"] = et
    df["date_et"] = et.dt.tz_localize(None).dt.normalize()
    t = et.dt.time
    df = df[(t >= dtime(9,30)) & (t < dtime(16,0))].copy()
    out = {"status":"OK", "rows":int(len(df)), "first":str(df["timestamp"].min()), "last":str(df["timestamp"].max()), "days":int(df["date_et"].nunique()), "june_events":[]}

    for event in [e for e in EVENTS if e["d0"] in ("2026-06-10","2026-06-17")]:
        d0 = pd.Timestamp(event["d0"])
        row = daily[daily["date"] == d0].iloc[0]
        atr = float(row["atr20_wilder"]); eh=float(row["high"]); el=float(row["low"])
        buy=eh+0.20*atr; sell=el-0.20*atr
        d1 = trading_days_after(daily, event["d0"])[0]
        day = df[df["date_et"] == d1]
        rec = {"d0":event["d0"], "d1":str(d1.date()), "buy_stop":buy, "sell_stop":sell}
        if day.empty:
            rec["status"]="D1_MISSING"
        else:
            trigger=None
            for _,bar in day.iterrows():
                buy_gap=float(bar["open"])>=buy; sell_gap=float(bar["open"])<=sell
                buy_hit=float(bar["high"])>=buy; sell_hit=float(bar["low"])<=sell
                if buy_gap: trigger={"direction":"LONG","price":float(bar["open"]),"time":bar["timestamp_et"],"fill":"GAP_OPEN"}; break
                if sell_gap: trigger={"direction":"SHORT","price":float(bar["open"]),"time":bar["timestamp_et"],"fill":"GAP_OPEN"}; break
                if buy_hit and sell_hit: trigger={"direction":"AMBIGUOUS_SAME_M1","time":bar["timestamp_et"]}; break
                if buy_hit: trigger={"direction":"LONG","price":buy,"time":bar["timestamp_et"],"fill":"TRIGGER"}; break
                if sell_hit: trigger={"direction":"SHORT","price":sell,"time":bar["timestamp_et"],"fill":"TRIGGER"}; break
            rec["status"]="TRIGGER" if trigger else "NO_TRIGGER"
            rec["trigger"]=trigger
        out["june_events"].append(rec)
    return out


def test_qqq_macro_m1_remote_replay():
    daily = fetch_daily()
    emit("DAILY_COVERAGE", {"rows":len(daily), "first":daily["date"].min(), "last":daily["date"].max(), "cols":list(daily.columns)})

    start = pd.Timestamp("2026-02-01T00:00:00Z")
    end = pd.Timestamp("2026-06-27T23:59:59Z")
    bid = rth(duka_fetch("B", start, end))
    ask = rth(duka_fetch("A", start, end))
    emit("DUKA_COVERAGE", {"bid_rows":len(bid), "ask_rows":len(ask), "bid_first":bid["timestamp"].min() if len(bid) else None, "bid_last":bid["timestamp"].max() if len(bid) else None})
    q = merge_quotes(bid, ask)
    emit("QUOTE_COVERAGE", {"rows":len(q), "days":q["date_et"].nunique(), "first":q["timestamp"].min(), "last":q["timestamp"].max()})
    emit("DAILY_CROSSCHECK", compare_daily(daily, q))

    results = [simulate_event(daily, q, e) for e in EVENTS]
    for r in results:
        emit("M1_EVENT_RESULT", r)
    trades = [r for r in results if r.get("status") == "TRADE"]
    summary = {
        "events":len(results),
        "trades":len(trades),
        "wins":sum(1 for r in trades if r["pnl_r"] > 0),
        "losses":sum(1 for r in trades if r["pnl_r"] < 0),
        "sum_r":sum(r["pnl_r"] for r in trades),
        "sum_trade_pct":sum(r["pnl_pct"] for r in trades),
        "compound_notional_pct":(pd.Series([1+r["pnl_pct"]/100 for r in trades]).prod()-1)*100 if trades else 0,
        "worst_mae_pct":min((r["mae_pct"] for r in trades), default=0),
        "statuses":pd.Series([r["status"] for r in results]).value_counts().to_dict(),
        "exit_reasons":pd.Series([r["exit_reason"] for r in trades]).value_counts().to_dict(),
    }
    emit("M1_STRATEGY_SUMMARY", summary)
    emit("YAHOO_JUNE_CROSSCHECK", yahoo_june_replay(daily, results))

    assert False, "QQQ_M1_REPLAY_COMPLETE_RESULTS_EMITTED_ABOVE"
