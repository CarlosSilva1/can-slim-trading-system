"""Temporary research test: compare frozen QQQ Macro Reset baseline with one
predefined trailing variant on the same 2024-2026 macro-event sample.

Baseline (frozen):
- CPI, FOMC, GDP Advance only; no Payroll
- D0 event range
- D+1 OCO only
- entry buffer = 0.20 * ATR20
- ATR20 = simple rolling mean of True Range over 20 D1 sessions
- hard stop = 2.0 * ATR20
- take = 2R
- time stop = close of 7th session after entry
- flat before next eligible macro event

Trailing candidate (predefined, not optimized):
- same entries and same initial 2 ATR hard stop
- no fixed 2R take
- after price first reaches +1R, arm trailing at that day's close
- from the NEXT session, Chandelier-style 2 ATR trail:
  LONG  = highest HIGH since activation - 2*ATR20(D0)
  SHORT = lowest LOW since activation + 2*ATR20(D0)
- trail only ratchets in favorable direction
- same 7-session time stop and Macro Shield
- same conservative D1 ambiguity handling
"""
from __future__ import annotations

import io
import json
from dataclasses import dataclass

import pandas as pd
import requests

DAILY_URL = "https://raw.githubusercontent.com/xunme1/stock_ranking/30bca2c5889b4d1c845b8228b41ef2947bc4a46d/data/raw/daily/QQQ.csv"

EVENTS = [
    ("CPI","2024-07-11"),("GDP","2024-07-25"),("FOMC","2024-07-31"),("CPI","2024-08-14"),
    ("CPI","2024-09-11"),("FOMC","2024-09-18"),("CPI","2024-10-10"),("GDP","2024-10-30"),
    ("FOMC","2024-11-07"),("CPI","2024-11-13"),("CPI","2024-12-11"),("FOMC","2024-12-18"),
    ("CPI","2025-01-15"),("FOMC","2025-01-29"),("GDP","2025-01-30"),("CPI","2025-02-12"),
    ("CPI","2025-03-12"),("FOMC","2025-03-19"),("GDP","2025-04-30"),("CPI","2025-04-10"),
    ("FOMC","2025-05-07"),("CPI","2025-05-13"),("CPI","2025-06-11"),("FOMC","2025-06-18"),
    ("GDP","2025-07-30"),("CPI","2025-07-15"),("FOMC","2025-07-30"),("CPI","2025-08-12"),
    ("CPI","2025-09-11"),("FOMC","2025-09-17"),("FOMC","2025-10-29"),("GDP","2025-10-30"),
    ("FOMC","2025-12-10"),("CPI","2025-12-18"),("CPI","2026-01-13"),("FOMC","2026-01-28"),
    ("CPI","2026-02-13"),("CPI","2026-03-11"),("FOMC","2026-03-18"),("CPI","2026-04-10"),
    ("FOMC","2026-04-29"),("GDP","2026-04-30"),("CPI","2026-05-12"),("CPI","2026-06-10"),
    ("FOMC","2026-06-17"),
]
EVENTS = sorted(set(EVENTS), key=lambda x: x[1])


def emit(tag, obj):
    print(tag + " " + json.dumps(obj, sort_keys=True, default=str))


def load_daily():
    r = requests.get(DAILY_URL, timeout=60)
    r.raise_for_status()
    d = pd.read_csv(io.StringIO(r.text.lstrip('\ufeff')))
    d['date'] = pd.to_datetime(d['date'])
    d = d.sort_values('date').reset_index(drop=True)
    pc = d.close.shift(1)
    tr = pd.concat([(d.high-d.low),(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1)
    d['atr20'] = tr.rolling(20).mean()
    d['ema21'] = d.close.ewm(span=21, adjust=False).mean()
    return d


def next_macro_after(d0):
    future = [pd.Timestamp(dt) for _,dt in EVENTS if pd.Timestamp(dt) > d0]
    return min(future) if future else None


def trade_entry(d, typ, d0s):
    d0 = pd.Timestamp(d0s)
    rows = d[d.date == d0]
    if rows.empty:
        return None
    r = rows.iloc[0]
    if pd.isna(r.atr20):
        return None
    future = d[d.date > d0]
    if future.empty:
        return None
    d1 = future.iloc[0]
    nxt = next_macro_after(d0)
    if nxt is not None and d1.date == nxt:
        return {'status':'NO_TRADE_NEXT_MACRO','event':typ,'d0':d0}
    atr=float(r.atr20); buy=float(r.high)+0.2*atr; sell=float(r.low)-0.2*atr
    # D+1 only. Conservative: if both sides touch inside same D1 bar, skip.
    buy_gap=float(d1.open)>=buy; sell_gap=float(d1.open)<=sell
    buy_hit=float(d1.high)>=buy; sell_hit=float(d1.low)<=sell
    if buy_gap and sell_gap:
        return {'status':'AMBIG_ENTRY','event':typ,'d0':d0}
    if buy_gap:
        direction='LONG'; ep=float(d1.open); fill='GAP_OPEN'
    elif sell_gap:
        direction='SHORT'; ep=float(d1.open); fill='GAP_OPEN'
    elif buy_hit and sell_hit:
        return {'status':'AMBIG_ENTRY','event':typ,'d0':d0}
    elif buy_hit:
        direction='LONG'; ep=buy; fill='TRIGGER'
    elif sell_hit:
        direction='SHORT'; ep=sell; fill='TRIGGER'
    else:
        return {'status':'NO_TRIGGER','event':typ,'d0':d0}
    return {'status':'ENTRY','event':typ,'d0':d0,'d1':d1.date,'direction':direction,'entry':ep,'atr':atr,'fill':fill,'buy':buy,'sell':sell}


def force_exit_day(d, entry_date, d0):
    sessions = d[d.date >= entry_date].date.tolist()
    time_day = sessions[6] if len(sessions)>=7 else sessions[-1]
    nxt = next_macro_after(d0)
    reason='TIME'
    force=time_day
    if nxt is not None:
        prior = d[d.date < nxt].date
        if len(prior):
            macro_day=prior.iloc[-1]
            if macro_day < force:
                force=macro_day; reason='MACRO'
    return force,reason


def run_baseline(d, ent):
    ep=ent['entry']; atr=ent['atr']; direction=ent['direction']; risk=2*atr
    stop=ep-risk if direction=='LONG' else ep+risk
    take=ep+2*risk if direction=='LONG' else ep-2*risk
    force,fr=force_exit_day(d, ent['d1'], ent['d0'])
    scan=d[(d.date>=ent['d1'])&(d.date<=force)]
    mae=0.;mfe=0.
    for _,x in scan.iterrows():
        if direction=='LONG':
            mae=min(mae,(x.low-ep)/risk);mfe=max(mfe,(x.high-ep)/risk);sl=x.low<=stop;tp=x.high>=take
        else:
            mae=min(mae,(ep-x.high)/risk);mfe=max(mfe,(ep-x.low)/risk);sl=x.high>=stop;tp=x.low<=take
        if sl and tp: xp=stop;why='STOP_SAME_BAR';xd=x.date;break
        if sl: xp=stop;why='STOP';xd=x.date;break
        if tp: xp=take;why='TAKE';xd=x.date;break
    else:
        x=scan.iloc[-1];xp=float(x.close);why=fr;xd=x.date
    rr=(xp-ep)/risk if direction=='LONG' else (ep-xp)/risk
    pct=((xp-ep)/ep*100) if direction=='LONG' else ((ep-xp)/ep*100)
    return {**ent,'exit':float(xp),'exit_date':xd,'exit_reason':why,'pnl_r':float(rr),'pnl_pct':float(pct),'mae_r':float(mae),'mfe_r':float(mfe)}


def run_atr_trailing(d, ent):
    ep=ent['entry']; atr=ent['atr']; direction=ent['direction']; risk=2*atr
    hard=ep-risk if direction=='LONG' else ep+risk
    plus1=ep+risk if direction=='LONG' else ep-risk
    force,fr=force_exit_day(d, ent['d1'], ent['d0'])
    scan=d[(d.date>=ent['d1'])&(d.date<=force)].copy()
    armed=False; active=False; extreme=None; trail=None; activation_date=None; mae=0.;mfe=0.
    for _,x in scan.iterrows():
        if direction=='LONG':
            mae=min(mae,(x.low-ep)/risk);mfe=max(mfe,(x.high-ep)/risk)
            # Existing hard stop always applies first.
            if x.low<=hard:
                xp=hard;why='HARD_STOP';xd=x.date;break
            if active:
                # Trail valid from session after activation. Ratchet using PRIOR favorable extreme;
                # after evaluating stop, incorporate today's high for next session.
                if x.low<=trail:
                    xp=trail;why='ATR_TRAIL';xd=x.date;break
                extreme=max(extreme,float(x.high));trail=max(trail,extreme-2*atr)
            elif x.high>=plus1:
                armed=True;activation_date=x.date;extreme=float(x.high);trail=extreme-2*atr
            if armed and x.date>activation_date:
                active=True
        else:
            mae=min(mae,(ep-x.high)/risk);mfe=max(mfe,(ep-x.low)/risk)
            if x.high>=hard:
                xp=hard;why='HARD_STOP';xd=x.date;break
            if active:
                if x.high>=trail:
                    xp=trail;why='ATR_TRAIL';xd=x.date;break
                extreme=min(extreme,float(x.low));trail=min(trail,extreme+2*atr)
            elif x.low<=plus1:
                armed=True;activation_date=x.date;extreme=float(x.low);trail=extreme+2*atr
            if armed and x.date>activation_date:
                active=True
    else:
        x=scan.iloc[-1];xp=float(x.close);why=fr;xd=x.date
    rr=(xp-ep)/risk if direction=='LONG' else (ep-xp)/risk
    pct=((xp-ep)/ep*100) if direction=='LONG' else ((ep-xp)/ep*100)
    return {**ent,'exit':float(xp),'exit_date':xd,'exit_reason':why,'pnl_r':float(rr),'pnl_pct':float(pct),'mae_r':float(mae),'mfe_r':float(mfe),'trail_armed':bool(armed)}


def metrics(trades):
    rs=[t['pnl_r'] for t in trades]; wins=[r for r in rs if r>0]; losses=[r for r in rs if r<0]
    eq=0.;peak=0.;mdd=0.;curve=[]
    for r in rs:
        eq+=r;peak=max(peak,eq);mdd=min(mdd,eq-peak);curve.append(eq)
    gross_win=sum(wins);gross_loss=-sum(losses)
    givebacks=[]
    for t in trades:
        if t['mfe_r']>0:
            givebacks.append((t['mfe_r']-t['pnl_r'])/t['mfe_r'])
    return {
        'trades':len(trades),'wins':len(wins),'losses':len(losses),'win_rate':len(wins)/len(trades)*100 if trades else 0,
        'total_r':sum(rs),'expectancy_r':sum(rs)/len(rs) if rs else 0,'pf':gross_win/gross_loss if gross_loss else None,
        'max_dd_r':mdd,'avg_win_r':sum(wins)/len(wins) if wins else 0,'avg_loss_r':sum(losses)/len(losses) if losses else 0,
        'median_r':float(pd.Series(rs).median()) if rs else 0,'worst_mae_r':min((t['mae_r'] for t in trades),default=0),
        'avg_mfe_r':sum(t['mfe_r'] for t in trades)/len(trades) if trades else 0,
        'avg_profit_giveback_pct':sum(givebacks)/len(givebacks)*100 if givebacks else 0,
        'exit_reasons':pd.Series([t['exit_reason'] for t in trades]).value_counts().to_dict(),
    }


def test_compare_baseline_vs_defined_atr_trailing():
    d=load_daily()
    entries=[];statuses=[]
    for typ,dt in EVENTS:
        ent=trade_entry(d,typ,dt)
        if ent is None: continue
        statuses.append(ent['status'])
        if ent['status']=='ENTRY':entries.append(ent)
    base=[run_baseline(d,e) for e in entries]
    trail=[run_atr_trailing(d,e) for e in entries]
    emit('SAMPLE',{'events_considered':len(EVENTS),'entries':len(entries),'statuses':pd.Series(statuses).value_counts().to_dict(),'first_entry':entries[0]['d0'] if entries else None,'last_entry':entries[-1]['d0'] if entries else None})
    emit('BASELINE_METRICS',metrics(base))
    emit('TRAILING_METRICS',metrics(trail))
    for b,t in zip(base,trail):
        emit('TRADE_COMPARE',{'event':b['event'],'d0':b['d0'],'direction':b['direction'],'baseline_r':b['pnl_r'],'baseline_exit':b['exit_reason'],'trail_r':t['pnl_r'],'trail_exit':t['exit_reason'],'trail_armed':t['trail_armed'],'mfe_r':b['mfe_r'],'mae_r':b['mae_r'],'delta_r':t['pnl_r']-b['pnl_r']})
    assert False, 'QQQ_TRAILING_COMPARISON_COMPLETE'
