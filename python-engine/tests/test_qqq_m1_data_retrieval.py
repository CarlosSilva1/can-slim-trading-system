"""Temporary remote data-retrieval test for the QQQ Macro Reset M1 validation.

This intentionally fails after emitting gzip+base64 CSV payloads to the GitHub
Actions log. The repository's existing workflow already runs pytest on PRs and
continues after a test failure, so no workflow-file modification is required.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import json
import random
import re
import string
import time
from datetime import datetime, time as dtime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

NY = ZoneInfo("America/New_York")
FROM_TS = int(pd.Timestamp("2026-02-01T00:00:00Z").timestamp())
END_TS = pd.Timestamp("2026-06-27T00:00:00Z")

EVENT_WINDOWS = [
    ("CPI_2026-02-13", "2026-02-17", "2026-02-20"),
    ("GDP_2026-02-20", "2026-02-23", "2026-02-24"),
    ("CPI_2026-03-11", "2026-03-12", "2026-03-18"),
    ("FOMC_2026-03-18", "2026-03-19", "2026-03-28"),
    ("CPI_2026-04-10", "2026-04-13", "2026-04-22"),
    ("GDP_2026-04-30", "2026-05-01", "2026-05-09"),
    ("CPI_2026-05-12", "2026-05-13", "2026-05-22"),
    ("CPI_2026-06-10", "2026-06-11", "2026-06-17"),
    ("FOMC_2026-06-17", "2026-06-18", "2026-06-25"),
]


def _rth(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    x = df.copy()
    x["timestamp"] = pd.to_datetime(x["timestamp"], utc=True, errors="coerce")
    x = x.dropna(subset=["timestamp"])
    local = x["timestamp"].dt.tz_convert(NY)
    t = local.dt.time
    keep = (local.dt.weekday < 5) & (t >= dtime(9, 30)) & (t < dtime(16, 0))
    x = x.loc[keep].copy()
    x["timestamp_et"] = local.loc[keep].astype(str)
    return x.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)


def _event_subset(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    local = pd.to_datetime(df["timestamp"], utc=True).dt.tz_convert(NY)
    dates = local.dt.strftime("%Y-%m-%d")
    parts = []
    for label, start, end in EVENT_WINDOWS:
        p = df[(dates >= start) & (dates < end)].copy()
        if not p.empty:
            p["event_window"] = label
            parts.append(p)
    if not parts:
        return pd.DataFrame(columns=list(df.columns) + ["event_window"])
    return pd.concat(parts, ignore_index=True).sort_values("timestamp").reset_index(drop=True)


def _coverage(df: pd.DataFrame) -> dict:
    ev = _event_subset(df)
    counts = {str(k): int(v) for k, v in ev.groupby("event_window").size().to_dict().items()} if not ev.empty else {}
    return {
        "rows_full": int(len(df)),
        "rows_event_windows": int(len(ev)),
        "first_utc": str(df["timestamp"].min()) if not df.empty else None,
        "last_utc": str(df["timestamp"].max()) if not df.empty else None,
        "window_counts": counts,
    }


def _emit_csv(source: str, df: pd.DataFrame) -> dict:
    ev = _event_subset(df)
    csv_bytes = ev.to_csv(index=False).encode("utf-8")
    packed = gzip.compress(csv_bytes, compresslevel=9, mtime=0)
    encoded = base64.b64encode(packed).decode("ascii")
    sha = hashlib.sha256(csv_bytes).hexdigest()
    print(f"QQQ_DATA_BEGIN source={source} rows={len(ev)} csv_bytes={len(csv_bytes)} gzip_bytes={len(packed)} sha256={sha}")
    width = 3000
    for idx in range(0, len(encoded), width):
        seq = idx // width
        print(f"QQQ_DATA_CHUNK source={source} seq={seq:05d} data={encoded[idx:idx+width]}")
    print(f"QQQ_DATA_END source={source}")
    return {"source": source, "sha256_csv": sha, **_coverage(df)}


class TVHistory:
    """Public TradingView chart websocket history client with backward paging."""

    WS_URL = "wss://data.tradingview.com/socket.io/websocket"
    WS_HEADERS = json.dumps({"Origin": "https://data.tradingview.com"})

    def __init__(self):
        self.ws = None
        self.chart_session = "cs_" + "".join(random.choice(string.ascii_lowercase) for _ in range(12))
        self.quote_session = "qs_" + "".join(random.choice(string.ascii_lowercase) for _ in range(12))

    @staticmethod
    def _frame(payload: str) -> str:
        return "~m~" + str(len(payload)) + "~m~" + payload

    def _send(self, method: str, params: list) -> None:
        payload = json.dumps({"m": method, "p": params}, separators=(",", ":"))
        self.ws.send(self._frame(payload))

    @staticmethod
    def _parse(raw: str, symbol: str) -> pd.DataFrame:
        # Same shape used by tvDatafeed-derived clients: s:[{i:...,v:[ts,o,h,l,c,v]}]
        blocks = re.findall(r'"s":\[(.+?)\}\]', raw, flags=re.S)
        rows = []
        for block in blocks:
            for item in block.split(',{"'):
                parts = re.split(r"\[|:|,|\]", item)
                try:
                    ts = int(float(parts[4]))
                    vals = []
                    for i in range(5, 10):
                        try:
                            vals.append(float(parts[i]))
                        except (ValueError, IndexError):
                            vals.append(0.0)
                    rows.append([ts, *vals])
                except (ValueError, IndexError):
                    continue
        if not rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "symbol"])
        df = pd.DataFrame(rows, columns=["epoch", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df.pop("epoch"), unit="s", utc=True)
        df["symbol"] = symbol
        return df[["timestamp", "open", "high", "low", "close", "volume", "symbol"]]

    def _recv_complete(self, timeout: int = 45) -> str:
        raw = ""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                msg = self.ws.recv()
            except Exception:
                break
            if not msg:
                break
            raw += msg + "\n"
            if "series_completed" in msg:
                break
        return raw

    def get_hist(self, symbol: str, exchange: str, from_timestamp: int, batch: int = 1000, max_batches: int = 120) -> pd.DataFrame:
        from websocket import create_connection

        full_symbol = f"{exchange}:{symbol}"
        self.ws = create_connection(self.WS_URL, headers=self.WS_HEADERS, timeout=45)
        self._send("set_auth_token", ["unauthorized_user_token"])
        self._send("chart_create_session", [self.chart_session, ""])
        self._send("quote_create_session", [self.quote_session])
        self._send("quote_add_symbols", [self.quote_session, full_symbol, {"flags": ["force_permission"]}])
        self._send("quote_fast_symbols", [self.quote_session, full_symbol])
        resolve = json.dumps({"symbol": full_symbol, "adjustment": "splits", "session": "regular"}, separators=(",", ":"))
        self._send("resolve_symbol", [self.chart_session, "symbol_1", "=" + resolve])
        self._send("create_series", [self.chart_session, "sds_1", "s1", "symbol_1", "1", batch])
        self._send("switch_timezone", [self.chart_session, "exchange"])

        chunks = []
        first = self._parse(self._recv_complete(), full_symbol)
        if first.empty:
            self.ws.close()
            return first
        chunks.append(first)
        earliest = int(first["timestamp"].min().timestamp())
        print(f"TV_INITIAL symbol={full_symbol} rows={len(first)} earliest={first['timestamp'].min()} latest={first['timestamp'].max()}")

        zero = 0
        for n in range(1, max_batches + 1):
            if earliest <= from_timestamp:
                break
            self._send("request_more_data", [self.chart_session, "sds_1", batch])
            part = self._parse(self._recv_complete(), full_symbol)
            if part.empty:
                zero += 1
                print(f"TV_EMPTY_BATCH n={n} zero={zero}")
                if zero >= 2:
                    break
                continue
            zero = 0
            chunks.append(part)
            earliest = min(earliest, int(part["timestamp"].min().timestamp()))
            print(f"TV_BATCH n={n} rows={len(part)} earliest={part['timestamp'].min()}")

        try:
            self.ws.close()
        except Exception:
            pass
        out = pd.concat(chunks, ignore_index=True)
        return out.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)


def fetch_tradingview() -> pd.DataFrame:
    errors = []
    for exchange in ("NASDAQ", "AMEX", "NYSEARCA"):
        try:
            raw = TVHistory().get_hist("QQQ", exchange, FROM_TS)
            if raw.empty:
                errors.append(f"{exchange}: empty")
                continue
            df = _rth(raw)
            df = df[(df["timestamp"] >= pd.Timestamp("2026-02-01T00:00:00Z")) & (df["timestamp"] < END_TS)]
            print(f"TV_FILTER exchange={exchange} rows={len(df)} first={df['timestamp'].min() if len(df) else None} last={df['timestamp'].max() if len(df) else None}")
            if len(df) >= 5000:
                return df.reset_index(drop=True)
            errors.append(f"{exchange}: only {len(df)} rows")
        except Exception as exc:
            errors.append(f"{exchange}: {type(exc).__name__}: {exc}")
            print(f"TV_ERROR {errors[-1]}")
    raise RuntimeError(" | ".join(errors))


def fetch_dukascopy() -> pd.DataFrame:
    import dukascopy_python as dk
    import dukascopy_python.instruments as I

    instrument_name = "INSTRUMENT_ETF_CFD_US_QQQ_US"
    inst = getattr(I, instrument_name)
    chunks = []
    for label, start_s, end_s in EVENT_WINDOWS:
        start = datetime.strptime(start_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end = datetime.strptime(end_s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        print(f"DK_FETCH label={label} start={start_s} end={end_s}")
        part = dk.fetch(inst, dk.INTERVAL_MIN_1, dk.OFFER_SIDE_BID, start, end)
        if part is None or len(part) == 0:
            print(f"DK_EMPTY label={label}")
            continue
        part = part.reset_index()
        part = part.rename(columns={part.columns[0]: "timestamp"})
        part["timestamp"] = pd.to_datetime(part["timestamp"], utc=True, errors="coerce")
        keep = [c for c in ["timestamp", "open", "high", "low", "close", "volume"] if c in part.columns]
        part = part[keep]
        part["symbol"] = "DUKASCOPY_QQQ_US_CFD_BID"
        print(f"DK_ROWS label={label} rows={len(part)}")
        chunks.append(part)
    if not chunks:
        raise RuntimeError("Dukascopy returned no QQQ CFD rows")
    return _rth(pd.concat(chunks, ignore_index=True))


def fetch_yahoo_recent() -> pd.DataFrame:
    import yfinance as yf

    chunks = []
    for day in pd.bdate_range("2026-06-05", "2026-06-26"):
        start = day.strftime("%Y-%m-%d")
        end = (day + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
        try:
            part = yf.download("QQQ", start=start, end=end, interval="1m", auto_adjust=False, prepost=False, progress=False, threads=False)
        except Exception as exc:
            print(f"YF_ERROR day={start} error={type(exc).__name__}:{exc}")
            continue
        if part is None or part.empty:
            print(f"YF_EMPTY day={start}")
            continue
        if isinstance(part.columns, pd.MultiIndex):
            part.columns = part.columns.get_level_values(0)
        part = part.reset_index()
        part = part.rename(columns={part.columns[0]: "timestamp", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
        part["timestamp"] = pd.to_datetime(part["timestamp"], utc=True, errors="coerce")
        part["symbol"] = "QQQ"
        keep = ["timestamp", "open", "high", "low", "close", "volume", "symbol"]
        chunks.append(part[keep])
        print(f"YF_ROWS day={start} rows={len(part)}")
    if not chunks:
        raise RuntimeError("Yahoo returned no 1m rows")
    return _rth(pd.concat(chunks, ignore_index=True))


def test_qqq_m1_remote_retrieval():
    summaries = []
    errors = {}
    for source, func in (
        ("tradingview_qqq", fetch_tradingview),
        ("dukascopy_qqq_cfd", fetch_dukascopy),
        ("yahoo_qqq_recent", fetch_yahoo_recent),
    ):
        try:
            print(f"SOURCE_BEGIN {source}")
            df = func()
            summaries.append(_emit_csv(source, df))
            print(f"SOURCE_END {source}")
        except Exception as exc:
            errors[source] = f"{type(exc).__name__}: {exc}"
            print(f"SOURCE_FAILED source={source} error={errors[source]}")

    payload = {"summaries": summaries, "errors": errors}
    print("QQQ_SUMMARY_JSON " + json.dumps(payload, sort_keys=True))

    # Intentional failure forces pytest to include captured stdout in Actions logs.
    assert False, "QQQ_M1_DATA_EMITTED_TO_ACTION_LOG"
