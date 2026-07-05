from __future__ import annotations

import csv
import io
import json
import math
import re
import statistics
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from functools import reduce
from html.parser import HTMLParser

START = date(2016, 1, 1)
END = date(2026, 6, 26)
WARMUP_START = date(2015, 1, 1)

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/QQQ"
BLS_BASE = "https://www.bls.gov/schedule/{year}/home.htm"
FED_CURRENT = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
FED_HIST = "https://www.federalreserve.gov/monetarypolicy/fomchistorical{year}.htm"
BEA_ARCHIVE = "https://www.bea.gov/news/archive"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135 Safari/537.36"
MONTHS = {m.lower(): i for i, m in enumerate([
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})


def fetch(url: str, params: dict | None = None) -> str:
    if params:
        url = url + ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", errors="replace")


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_tr = False
        self.in_cell = False
        self.cell = []
        self.row = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.in_tr = True
            self.row = []
        elif self.in_tr and tag in ("td", "th"):
            self.in_cell = True
            self.cell = []

    def handle_data(self, data):
        if self.in_cell:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            text = " ".join("".join(self.cell).split())
            self.row.append(text)
            self.in_cell = False
        elif tag == "tr" and self.in_tr:
            if self.row:
                self.rows.append(self.row)
            self.in_tr = False


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.current = dict(attrs).get("href")
            self.text = []

    def handle_data(self, data):
        if self.current is not None:
            self.text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            self.links.append((self.current, " ".join("".join(self.text).split())))
            self.current = None
            self.text = []


class SelectParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.select_name = None
        self.in_option = False
        self.option_value = None
        self.option_text = []
        self.options = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select":
            self.select_name = attrs.get("name")
        elif tag == "option" and self.select_name:
            self.in_option = True
            self.option_value = attrs.get("value")
            self.option_text = []

    def handle_data(self, data):
        if self.in_option:
            self.option_text.append(data)

    def handle_endtag(self, tag):
        if tag == "option" and self.in_option:
            self.options.append((self.select_name, self.option_value, " ".join("".join(self.option_text).split())))
            self.in_option = False
        elif tag == "select":
            self.select_name = None


def parse_month_day(text: str, year: int) -> date | None:
    cleaned = re.sub(r"[,\u00a0]", " ", text)
    cleaned = " ".join(cleaned.split())
    m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?\s+(\d{1,2})\b", cleaned, re.I)
    if not m:
        return None
    mon = MONTHS[m.group(1).lower()[:3]]
    return date(year, mon, int(m.group(2)))


def fetch_qqq_daily() -> list[dict]:
    p1 = int(datetime(WARMUP_START.year, WARMUP_START.month, WARMUP_START.day, tzinfo=timezone.utc).timestamp())
    p2 = int(datetime(END.year, END.month, END.day, tzinfo=timezone.utc).timestamp()) + 86400
    raw = fetch(YAHOO_CHART, {
        "period1": p1,
        "period2": p2,
        "interval": "1d",
        "events": "div,splits",
        "includeAdjustedClose": "true",
    })
    data = json.loads(raw)["chart"]["result"][0]
    ts = data["timestamp"]
    quote = data["indicators"]["quote"][0]
    rows = []
    for i, t in enumerate(ts):
        vals = {k: quote[k][i] for k in ("open", "high", "low", "close", "volume")}
        if any(vals[k] is None for k in ("open", "high", "low", "close")):
            continue
        d = datetime.fromtimestamp(t, tz=timezone.utc).date()
        rows.append({"date": d, **{k: float(v) for k, v in vals.items()}})
    rows.sort(key=lambda x: x["date"])

    trs = []
    ema = None
    alpha = 2 / (21 + 1)
    for i, r in enumerate(rows):
        pc = rows[i - 1]["close"] if i else r["close"]
        tr = max(r["high"] - r["low"], abs(r["high"] - pc), abs(r["low"] - pc))
        trs.append(tr)
        r["atr20"] = sum(trs[i - 19:i + 1]) / 20 if i >= 19 else None
        ema = r["close"] if ema is None else alpha * r["close"] + (1 - alpha) * ema
        r["ema21"] = ema
    return rows


def fetch_cpi_dates() -> list[dict]:
    out = []
    diagnostics = {}
    for year in range(2016, 2027):
        html = fetch(BLS_BASE.format(year=year))
        p = TableParser(); p.feed(html)
        year_dates = []
        for row in p.rows:
            joined = " | ".join(row)
            if "Consumer Price Index" not in joined:
                continue
            # Exclude special/local CPI series if any; the national release is exactly named in a cell.
            if not any(c.strip() == "Consumer Price Index" for c in row):
                continue
            d = None
            for cell in row:
                d = parse_month_day(cell, year)
                if d:
                    break
            if d and START <= d <= END:
                year_dates.append(d)
        year_dates = sorted(set(year_dates))
        diagnostics[str(year)] = [str(d) for d in year_dates]
        out.extend({"date": d, "type": "CPI", "source": "BLS official schedule"} for d in year_dates)
    return out, diagnostics


def fetch_fomc_dates() -> tuple[list[dict], dict]:
    out = []
    diagnostics = {}
    urls = [("current", FED_CURRENT)] + [(str(y), FED_HIST.format(year=y)) for y in range(2016, 2021)]
    for label, url in urls:
        html = fetch(url)
        lp = LinkParser(); lp.feed(html)
        candidates = []
        for href, text in lp.links:
            m = re.search(r"monetary(20\d{6})a\.htm", href or "", re.I)
            if m:
                d = datetime.strptime(m.group(1), "%Y%m%d").date()
                if START <= d <= END:
                    candidates.append(d)
        candidates = sorted(set(candidates))
        diagnostics[label] = [str(d) for d in candidates]
        out.extend({"date": d, "type": "FOMC", "source": "Federal Reserve official statement calendar"} for d in candidates)

    # Emergency/unscheduled statement dates cannot satisfy T-1 flat planning. Keep only dates shown
    # as regular meetings on official calendars. Historical pages sometimes expose emergency statement
    # links too, so exclude known unscheduled 2020 policy actions and any extra statement-only dates.
    unscheduled = {
        date(2020, 3, 3), date(2020, 3, 15),
    }
    out = [x for x in out if x["date"] not in unscheduled]
    return out, diagnostics


def discover_bea_product_id() -> tuple[str, list]:
    html = fetch(BEA_ARCHIVE)
    p = SelectParser(); p.feed(html)
    matches = [(n, v, t) for n, v, t in p.options if t.strip() == "Gross Domestic Product"]
    if not matches:
        raise RuntimeError("BEA GDP product option not found")
    return matches[0][1], matches


def fetch_bea_archive_gdp_dates() -> tuple[list[dict], dict]:
    product_id, matches = discover_bea_product_id()
    out = []
    diagnostics = {"product_id": product_id, "product_matches": matches, "years": {}}
    for year in range(2016, 2025):
        html = fetch(BEA_ARCHIVE, {
            "field_related_product_target_id": product_id,
            "field_release_year_value": str(year),
        })
        lp = LinkParser(); lp.feed(html)
        release_links = []
        for href, text in lp.links:
            if not href or "/news/" not in href:
                continue
            txt = text.lower()
            if "gross domestic product" in txt and "advance estimate" in txt:
                release_links.append((href, text))
        # Fallback: the archive result title may be abbreviated. Collect GDP release links and inspect page title.
        if not release_links:
            for href, text in lp.links:
                if href and re.search(r"/news/20\d{2}/gross-domestic-product", href, re.I):
                    release_links.append((href, text))
        seen = set()
        year_dates = []
        inspected = []
        for href, text in release_links:
            if href.startswith("/"):
                href = "https://www.bea.gov" + href
            if href in seen:
                continue
            seen.add(href)
            page = fetch(href)
            title_m = re.search(r"<h1[^>]*>(.*?)</h1>", page, re.I | re.S)
            title = re.sub(r"<[^>]+>", " ", title_m.group(1) if title_m else text)
            title = " ".join(title.split())
            if "Advance Estimate" not in title and "advance estimate" not in page.lower()[:12000]:
                continue
            # Prefer explicit release date metadata or time element.
            ds = []
            for pat in [
                r'property="article:published_time"\s+content="(20\d{2}-\d{2}-\d{2})',
                r'<time[^>]*datetime="(20\d{2}-\d{2}-\d{2})',
                r'Release Date\s*</[^>]+>\s*<[^>]+>\s*([A-Z][a-z]+\s+\d{1,2},\s+20\d{2})',
            ]:
                m = re.search(pat, page, re.I | re.S)
                if m:
                    val = m.group(1)
                    try:
                        d = datetime.strptime(val[:10], "%Y-%m-%d").date() if re.match(r"\d{4}-", val) else datetime.strptime(val, "%B %d, %Y").date()
                        ds.append(d)
                    except ValueError:
                        pass
            if not ds:
                # URL is normally /news/YYYY/gross-domestic-product-...-YYYYMMDD
                m = re.search(r"(20\d{6})(?:\D|$)", href)
                if m:
                    ds.append(datetime.strptime(m.group(1), "%Y%m%d").date())
            if ds:
                d = ds[0]
                if START <= d <= END:
                    year_dates.append(d)
                    inspected.append({"date": str(d), "title": title, "url": href})
        year_dates = sorted(set(year_dates))
        diagnostics["years"][str(year)] = inspected
        out.extend({"date": d, "type": "GDP", "source": "BEA official archive"} for d in year_dates)

    # 2025-2026 actual advance GDP release dates in the study window. These are audited against BEA's
    # release schedule/archive context; Q3 2025 advance was canceled and therefore is deliberately absent.
    recent = [
        date(2025, 1, 30), date(2025, 4, 30), date(2025, 7, 30),
        date(2026, 2, 20), date(2026, 4, 30),
    ]
    out.extend({"date": d, "type": "GDP", "source": "BEA official release schedule/recent release"} for d in recent if START <= d <= END)
    diagnostics["recent_manual_audited"] = [str(d) for d in recent]
    return out, diagnostics


def dedupe_events(*groups) -> list[dict]:
    by_date = {}
    for group in groups:
        for e in group:
            d = e["date"]
            by_date.setdefault(d, {"date": d, "types": set(), "sources": set()})
            by_date[d]["types"].add(e["type"])
            by_date[d]["sources"].add(e["source"])
    out = []
    for d, v in sorted(by_date.items()):
        out.append({"date": d, "type": "+".join(sorted(v["types"])), "sources": sorted(v["sources"])})
    return out


def build_entry(rows, idx, events, event_idx):
    ev = events[event_idx]
    d0 = ev["date"]
    if d0 not in idx:
        return {"status": "NO_D0_TRADING_SESSION", **ev}
    i = idx[d0]
    r = rows[i]
    if r["atr20"] is None or i + 1 >= len(rows):
        return {"status": "NO_ATR_OR_D1", **ev}
    d1 = rows[i + 1]
    nxt = events[event_idx + 1]["date"] if event_idx + 1 < len(events) else None
    atr = r["atr20"]
    buy = r["high"] + 0.20 * atr
    sell = r["low"] - 0.20 * atr
    base = {
        "status": None, "event": ev["type"], "d0": d0, "d1": d1["date"], "next_macro": nxt,
        "eh": r["high"], "el": r["low"], "atr": atr, "buy": buy, "sell": sell,
    }
    if nxt and d1["date"] == nxt:
        return {**base, "status": "NO_TRADE_NEXT_MACRO_D1"}
    bg = d1["open"] >= buy
    sg = d1["open"] <= sell
    bh = d1["high"] >= buy
    sh = d1["low"] <= sell
    if (bg and sg) or (bh and sh and not bg and not sg):
        return {**base, "status": "AMBIGUOUS_D1_OCO"}
    if bg:
        direction, ep, fill = "LONG", d1["open"], "GAP_OPEN"
    elif sg:
        direction, ep, fill = "SHORT", d1["open"], "GAP_OPEN"
    elif bh:
        direction, ep, fill = "LONG", buy, "TRIGGER"
    elif sh:
        direction, ep, fill = "SHORT", sell, "TRIGGER"
    else:
        return {**base, "status": "NO_TRIGGER_D1"}
    return {**base, "status": "ENTRY", "direction": direction, "entry": ep, "fill": fill}


def force_exit_day(rows, idx, ent):
    start = idx[ent["d1"]]
    time_day = rows[min(start + 6, len(rows) - 1)]["date"]
    force, reason = time_day, "TIME_STOP"
    nxt = ent["next_macro"]
    if nxt:
        prior = [r["date"] for r in rows if r["date"] < nxt]
        if prior:
            macro_day = prior[-1]
            if macro_day < force:
                force, reason = macro_day, "MACRO_SHIELD"
    return force, reason


def run_baseline(rows, idx, ent):
    ep, atr, di = ent["entry"], ent["atr"], ent["direction"]
    risk = 2 * atr
    stop = ep - risk if di == "LONG" else ep + risk
    take = ep + 2 * risk if di == "LONG" else ep - 2 * risk
    force, fr = force_exit_day(rows, idx, ent)
    mae_r = 0.0; mfe_r = 0.0
    for x in rows[idx[ent["d1"]]:idx[force] + 1]:
        if di == "LONG":
            mae_r = min(mae_r, (x["low"] - ep) / risk)
            mfe_r = max(mfe_r, (x["high"] - ep) / risk)
            sl, tp = x["low"] <= stop, x["high"] >= take
        else:
            mae_r = min(mae_r, (ep - x["high"]) / risk)
            mfe_r = max(mfe_r, (ep - x["low"]) / risk)
            sl, tp = x["high"] >= stop, x["low"] <= take
        if sl and tp:
            xp, why, xd = stop, "STOP_SAME_BAR_CONSERVATIVE", x["date"]; break
        if sl:
            xp, why, xd = stop, "STOP", x["date"]; break
        if tp:
            xp, why, xd = take, "TAKE", x["date"]; break
    else:
        x = rows[idx[force]]
        xp, why, xd = x["close"], fr, force
    rr = (xp - ep) / risk if di == "LONG" else (ep - xp) / risk
    return {**ent, "model": "BASELINE_2R", "exit": xp, "exit_date": xd, "exit_reason": why, "pnl_r": rr, "mae_r": mae_r, "mfe_r": mfe_r}


def run_ema21(rows, idx, ent):
    ep, atr, di = ent["entry"], ent["atr"], ent["direction"]
    risk = 2 * atr
    stop = ep - risk if di == "LONG" else ep + risk
    plus1 = ep + risk if di == "LONG" else ep - risk
    force, fr = force_exit_day(rows, idx, ent)
    mae_r = 0.0; mfe_r = 0.0; armed = False; signal_date = None
    start_i, force_i = idx[ent["d1"]], idx[force]
    i = start_i
    while i <= force_i:
        x = rows[i]
        if di == "LONG":
            mae_r = min(mae_r, (x["low"] - ep) / risk)
            mfe_r = max(mfe_r, (x["high"] - ep) / risk)
            # Conservative same-bar order: hard stop dominates +1R activation ambiguity.
            if x["low"] <= stop:
                xp, why, xd = stop, "STOP", x["date"]; break
            if not armed and x["high"] >= plus1:
                armed = True
            if armed and x["close"] < x["ema21"]:
                signal_date = x["date"]
                if i + 1 <= force_i:
                    xp, why, xd = rows[i + 1]["open"], "EMA21_NEXT_OPEN", rows[i + 1]["date"]
                else:
                    xp, why, xd = x["close"], fr, x["date"]
                break
        else:
            mae_r = min(mae_r, (ep - x["high"]) / risk)
            mfe_r = max(mfe_r, (ep - x["low"]) / risk)
            if x["high"] >= stop:
                xp, why, xd = stop, "STOP", x["date"]; break
            if not armed and x["low"] <= plus1:
                armed = True
            if armed and x["close"] > x["ema21"]:
                signal_date = x["date"]
                if i + 1 <= force_i:
                    xp, why, xd = rows[i + 1]["open"], "EMA21_NEXT_OPEN", rows[i + 1]["date"]
                else:
                    xp, why, xd = x["close"], fr, x["date"]
                break
        i += 1
    else:
        x = rows[force_i]
        xp, why, xd = x["close"], fr, force
    rr = (xp - ep) / risk if di == "LONG" else (ep - xp) / risk
    return {**ent, "model": "EMA21_AFTER_1R", "exit": xp, "exit_date": xd, "exit_reason": why, "pnl_r": rr, "mae_r": mae_r, "mfe_r": mfe_r, "ema_armed": armed, "ema_signal_date": signal_date}


def metrics(trades):
    rs = [t["pnl_r"] for t in trades]
    wins = [r for r in rs if r > 0]
    losses = [r for r in rs if r < 0]
    eq = peak = 0.0; mdd = 0.0; max_neg_streak = streak = 0
    for r in rs:
        eq += r; peak = max(peak, eq); mdd = min(mdd, eq - peak)
        if r < 0:
            streak += 1; max_neg_streak = max(max_neg_streak, streak)
        else:
            streak = 0
    gw, gl = sum(wins), -sum(losses)
    return {
        "trades": len(rs), "wins": len(wins), "losses": len(losses),
        "win_rate_pct": len(wins) / len(rs) * 100 if rs else 0.0,
        "total_r": sum(rs), "expectancy_r": statistics.mean(rs) if rs else 0.0,
        "median_r": statistics.median(rs) if rs else 0.0,
        "profit_factor": gw / gl if gl else None,
        "max_closed_dd_r": mdd,
        "avg_win_r": statistics.mean(wins) if wins else 0.0,
        "avg_loss_r": statistics.mean(losses) if losses else 0.0,
        "max_negative_streak": max_neg_streak,
        "exit_reasons": {k: sum(1 for t in trades if t["exit_reason"] == k) for k in sorted(set(t["exit_reason"] for t in trades))},
    }


def subset(trades, start_d, end_d):
    return [t for t in trades if start_d <= t["d0"] <= end_d]


def paired_stats(base, ema):
    pairs = []
    for b, e in zip(base, ema):
        assert b["d0"] == e["d0"] and b["event"] == e["event"] and b["entry"] == e["entry"]
        pairs.append({"d0": b["d0"], "event": b["event"], "base_r": b["pnl_r"], "ema_r": e["pnl_r"], "delta_r": e["pnl_r"] - b["pnl_r"], "base_exit": b["exit_reason"], "ema_exit": e["exit_reason"]})
    deltas = [p["delta_r"] for p in pairs]
    loo = []
    for i in range(len(deltas)):
        loo.append(sum(deltas[:i] + deltas[i + 1:]))
    return {
        "pairs": len(pairs),
        "ema_better": sum(d > 1e-12 for d in deltas),
        "baseline_better": sum(d < -1e-12 for d in deltas),
        "same": sum(abs(d) <= 1e-12 for d in deltas),
        "total_delta_r": sum(deltas),
        "mean_delta_r": statistics.mean(deltas) if deltas else 0.0,
        "median_delta_r": statistics.median(deltas) if deltas else 0.0,
        "changed_trade_count": sum(abs(d) > 1e-12 for d in deltas),
        "leave_one_out_min_total_delta_r": min(loo) if loo else 0.0,
        "leave_one_out_max_total_delta_r": max(loo) if loo else 0.0,
        "leave_one_out_positive_count": sum(x > 0 for x in loo),
        "leave_one_out_nonpositive_count": sum(x <= 0 for x in loo),
        "largest_positive_delta": max(deltas) if deltas else 0.0,
        "largest_negative_delta": min(deltas) if deltas else 0.0,
        "top_abs_delta_trades": sorted(pairs, key=lambda p: abs(p["delta_r"]), reverse=True)[:10],
    }


def audit(base, ema, events):
    violations = []
    for model, trades in [("BASE", base), ("EMA", ema)]:
        for i, t in enumerate(trades, 1):
            if t["direction"] == "LONG" and t["fill"] == "TRIGGER" and abs(t["entry"] - t["buy"]) > 1e-8:
                violations.append([model, i, "LONG_TRIGGER_ENTRY_MISMATCH"])
            if t["direction"] == "SHORT" and t["fill"] == "TRIGGER" and abs(t["entry"] - t["sell"]) > 1e-8:
                violations.append([model, i, "SHORT_TRIGGER_ENTRY_MISMATCH"])
            if t["exit_reason"].startswith("STOP") and abs(t["pnl_r"] + 1.0) > 1e-8:
                violations.append([model, i, "STOP_NOT_MINUS_1R", t["pnl_r"]])
            if model == "BASE" and t["exit_reason"] == "TAKE" and abs(t["pnl_r"] - 2.0) > 1e-8:
                violations.append([model, i, "TAKE_NOT_PLUS_2R", t["pnl_r"]])
    duplicate_dates = [str(d) for d in sorted({e["date"] for e in events if sum(x["date"] == e["date"] for x in events) > 1})]
    return {"passed": not violations and not duplicate_dates, "violations": violations, "duplicate_event_dates_after_dedupe": duplicate_dates}


def main():
    rows = fetch_qqq_daily()
    rows = [r for r in rows if r["date"] <= END]
    idx = {r["date"]: i for i, r in enumerate(rows)}

    cpi, cpi_diag = fetch_cpi_dates()
    fomc, fomc_diag = fetch_fomc_dates()
    gdp, gdp_diag = fetch_bea_archive_gdp_dates()
    events = dedupe_events(cpi, fomc, gdp)
    events = [e for e in events if START <= e["date"] <= END]

    entry_records = [build_entry(rows, idx, events, i) for i in range(len(events))]
    entries = [e for e in entry_records if e["status"] == "ENTRY"]
    base = [run_baseline(rows, idx, e) for e in entries]
    ema = [run_ema21(rows, idx, e) for e in entries]

    print("DATA_COVERAGE " + json.dumps({
        "qqq_rows_total_with_warmup": len(rows),
        "qqq_first": str(rows[0]["date"]), "qqq_last": str(rows[-1]["date"]),
        "study_start": str(START), "study_end": str(END),
        "event_count_deduped": len(events),
        "event_type_counts": {k: sum(k in e["type"].split("+") for e in events) for k in ("CPI", "FOMC", "GDP")},
        "combined_event_days": [{"date": str(e["date"]), "type": e["type"]} for e in events if "+" in e["type"]],
        "entry_status_counts": {k: sum(1 for e in entry_records if e["status"] == k) for k in sorted(set(e["status"] for e in entry_records))},
    }, sort_keys=True))
    print("CPI_DIAGNOSTIC " + json.dumps(cpi_diag, sort_keys=True))
    print("FOMC_DIAGNOSTIC " + json.dumps(fomc_diag, sort_keys=True))
    print("GDP_DIAGNOSTIC " + json.dumps(gdp_diag, sort_keys=True))

    print("LOCKED_RULES " + json.dumps({
        "baseline": "0.20 ATR20 SMA-TR buffer; D+1 OCO only; 2 ATR hard stop=1R; fixed take 2R; 7-session time stop; Macro Shield",
        "challenger": "same entry/stop; +1R arms EMA21; long close<EMA21 or short close>EMA21 exits next open; no fixed take; same 7-session time stop and Macro Shield",
        "no_optimization": True,
        "same_day_events": "deduped into one D0 range / one OCO",
        "D1_ambiguity": "both OCO sides touched same D1 bar without gap -> no trade",
        "same_bar_stop_take": "stop first conservative",
    }, sort_keys=True))

    print("FULL_BASELINE " + json.dumps(metrics(base), sort_keys=True))
    print("FULL_EMA21 " + json.dumps(metrics(ema), sort_keys=True))
    print("FULL_PAIRED " + json.dumps(paired_stats(base, ema), sort_keys=True, default=str))

    blocks = [
        ("HISTORICAL_HOLDOUT_2016_2023", date(2016,1,1), date(2023,12,31)),
        ("DESIGN_WINDOW_2024_2026H1", date(2024,1,1), END),
        ("2016_2017", date(2016,1,1), date(2017,12,31)),
        ("2018_2019", date(2018,1,1), date(2019,12,31)),
        ("2020_2021", date(2020,1,1), date(2021,12,31)),
        ("2022_2023", date(2022,1,1), date(2023,12,31)),
        ("2024_2025", date(2024,1,1), date(2025,12,31)),
        ("2026_H1", date(2026,1,1), END),
    ]
    for name, s, e in blocks:
        b = subset(base, s, e); m = subset(ema, s, e)
        print("BLOCK " + json.dumps({"name": name, "start": str(s), "end": str(e), "baseline": metrics(b), "ema21": metrics(m), "paired": paired_stats(b, m)}, sort_keys=True, default=str))

    for year in range(2016, 2027):
        b = subset(base, date(year,1,1), min(date(year,12,31), END))
        m = subset(ema, date(year,1,1), min(date(year,12,31), END))
        print("YEAR " + json.dumps({"year": year, "baseline": metrics(b), "ema21": metrics(m), "paired": paired_stats(b, m)}, sort_keys=True, default=str))

    for event_type in ("CPI", "FOMC", "GDP"):
        b = [t for t in base if event_type in t["event"].split("+")]
        m = [t for t in ema if event_type in t["event"].split("+")]
        print("EVENT_TYPE " + json.dumps({"event_type": event_type, "baseline": metrics(b), "ema21": metrics(m), "paired": paired_stats(b, m)}, sort_keys=True, default=str))

    print("AUDIT " + json.dumps(audit(base, ema, events), sort_keys=True))


if __name__ == "__main__":
    main()
