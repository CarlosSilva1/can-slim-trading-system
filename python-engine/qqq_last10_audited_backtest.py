import csv, io, json, urllib.request
from datetime import datetime

URL='https://raw.githubusercontent.com/xunme1/stock_ranking/30bca2c5889b4d1c845b8228b41ef2947bc4a46d/data/raw/daily/QQQ.csv'
EVENTS=[
('CPI','2026-02-13'),
('GDP','2026-02-20'),
('CPI','2026-03-11'),
('FOMC','2026-03-18'),
('CPI','2026-04-10'),
('FOMC','2026-04-29'),
('GDP','2026-04-30'),
('CPI','2026-05-12'),
('CPI','2026-06-10'),
('FOMC','2026-06-17'),
]
raw=urllib.request.urlopen(URL,timeout=60).read().decode('utf-8-sig')
rows=[]
for r in csv.DictReader(io.StringIO(raw)):
    rows.append({'date':datetime.strptime(r['date'],'%Y-%m-%d').date(),'open':float(r['open']),'high':float(r['high']),'low':float(r['low']),'close':float(r['close'])})
rows.sort(key=lambda x:x['date']); idx={r['date']:i for i,r in enumerate(rows)}
trs=[]
for i,r in enumerate(rows):
    pc=rows[i-1]['close'] if i else r['close']
    trs.append(max(r['high']-r['low'],abs(r['high']-pc),abs(r['low']-pc)))
for i,r in enumerate(rows):
    r['atr20']=sum(trs[i-19:i+1])/20 if i>=19 else None

event_dates=[datetime.strptime(d,'%Y-%m-%d').date() for _,d in EVENTS]
def next_macro(d0):
    z=[d for d in event_dates if d>d0]
    return min(z) if z else None

results=[]
for typ,ds in EVENTS:
    d0=datetime.strptime(ds,'%Y-%m-%d').date(); i=idx[d0]; r=rows[i]; atr=r['atr20']; d1=rows[i+1]
    nxt=next_macro(d0)
    rec={'event':typ,'d0':str(d0),'d1':str(d1['date']),'eh':r['high'],'el':r['low'],'atr20':atr,'buy_stop':r['high']+.2*atr,'sell_stop':r['low']-.2*atr}
    if nxt and d1['date']==nxt:
        rec['status']='NO_TRADE_NEXT_MACRO_D1';results.append(rec);continue
    buy=rec['buy_stop'];sell=rec['sell_stop']
    bg=d1['open']>=buy;sg=d1['open']<=sell;bh=d1['high']>=buy;sh=d1['low']<=sell
    if bg and sg or (bh and sh and not bg and not sg):
        rec['status']='AMBIGUOUS_D1';results.append(rec);continue
    if bg:direction='LONG';ep=d1['open'];fill='GAP_OPEN'
    elif sg:direction='SHORT';ep=d1['open'];fill='GAP_OPEN'
    elif bh:direction='LONG';ep=buy;fill='TRIGGER'
    elif sh:direction='SHORT';ep=sell;fill='TRIGGER'
    else:
        rec['status']='NO_TRIGGER_D1';results.append(rec);continue
    risk=2*atr; stop=ep-risk if direction=='LONG' else ep+risk; take=ep+2*risk if direction=='LONG' else ep-2*risk
    sessions=rows[i+1:]
    time_day=sessions[6]['date'] if len(sessions)>=7 else sessions[-1]['date']
    force=time_day; force_reason='TIME_STOP'
    if nxt:
        prior=max(rr['date'] for rr in rows if rr['date']<nxt)
        if prior<force:
            force=prior;force_reason='MACRO_SHIELD'
    mae_pct=0.0;mfe_pct=0.0
    exitp=None;reason=None;exitd=None
    for x in rows[idx[d1['date']]:idx[force]+1]:
        if direction=='LONG':
            mae_pct=min(mae_pct,(x['low']-ep)/ep*100);mfe_pct=max(mfe_pct,(x['high']-ep)/ep*100);sl=x['low']<=stop;tp=x['high']>=take
        else:
            mae_pct=min(mae_pct,(ep-x['high'])/ep*100);mfe_pct=max(mfe_pct,(ep-x['low'])/ep*100);sl=x['high']>=stop;tp=x['low']<=take
        if sl and tp:
            exitp=stop;reason='STOP_SAME_BAR_CONSERVATIVE';exitd=x['date'];break
        if sl:
            exitp=stop;reason='STOP';exitd=x['date'];break
        if tp:
            exitp=take;reason='TAKE';exitd=x['date'];break
    if exitp is None:
        x=rows[idx[force]];exitp=x['close'];reason=force_reason;exitd=force
    pnl_pct=(exitp-ep)/ep*100 if direction=='LONG' else (ep-exitp)/ep*100
    pnl_r=(exitp-ep)/risk if direction=='LONG' else (ep-exitp)/risk
    rec.update({'status':'TRADE','direction':direction,'fill':fill,'entry':ep,'stop':stop,'take':take,'exit':exitp,'exit_date':str(exitd),'exit_reason':reason,'pnl_pct':pnl_pct,'pnl_r':pnl_r,'mae_pct':mae_pct,'mfe_pct':mfe_pct})
    results.append(rec)

tr=[r for r in results if r['status']=='TRADE']
eq=0.0;peak=0.0;mdd=0.0
for r in tr:
    eq+=r['pnl_r'];peak=max(peak,eq);mdd=min(mdd,eq-peak);r['equity_r']=eq;r['drawdown_r']=eq-peak
wins=[r for r in tr if r['pnl_r']>0];losses=[r for r in tr if r['pnl_r']<0]
gw=sum(r['pnl_r'] for r in wins);gl=-sum(r['pnl_r'] for r in losses)
summary={'events':len(results),'trades':len(tr),'no_trade':len(results)-len(tr),'wins':len(wins),'losses':len(losses),'win_rate_pct':len(wins)/len(tr)*100 if tr else 0,'total_r':sum(r['pnl_r'] for r in tr),'sum_trade_pct':sum(r['pnl_pct'] for r in tr),'compound_notional_pct':(__import__('functools').reduce(lambda a,b:a*(1+b['pnl_pct']/100),tr,1)-1)*100 if tr else 0,'expectancy_r':sum(r['pnl_r'] for r in tr)/len(tr) if tr else 0,'profit_factor':gw/gl if gl else None,'max_closed_dd_r':mdd,'worst_mae_pct':min((r['mae_pct'] for r in tr),default=0),'exit_reasons':{k:sum(1 for r in tr if r['exit_reason']==k) for k in sorted(set(r['exit_reason'] for r in tr))}}
print('AUDIT_RULES '+json.dumps({'atr':'SMA20 True Range incl D0','buffer':'0.20 ATR20','entry':'D+1 OCO only','gap_fill':'D+1 open if open beyond trigger','stop':'2 ATR20 = 1R','take':'2R','time_stop':'7 sessions from D+1','macro_shield':'exit prior session close before next eligible event','ambiguity':'if both sides touch same D1 bar without gap, no trade'},sort_keys=True))
for n,r in enumerate(results,1):print('EVENT_%02d '%n+json.dumps(r,sort_keys=True))
print('SUMMARY '+json.dumps(summary,sort_keys=True))
# invariant audit
viol=[]
for n,r in enumerate(results,1):
    if r['status']=='TRADE':
        if r['direction']=='LONG' and r['fill']=='TRIGGER' and abs(r['entry']-r['buy_stop'])>1e-8:viol.append([n,'LONG_TRIGGER_ENTRY_MISMATCH'])
        if r['direction']=='SHORT' and r['fill']=='TRIGGER' and abs(r['entry']-r['sell_stop'])>1e-8:viol.append([n,'SHORT_TRIGGER_ENTRY_MISMATCH'])
        if r['exit_reason'].startswith('STOP') and abs(r['pnl_r']+1)>1e-8:viol.append([n,'STOP_NOT_MINUS_1R',r['pnl_r']])
        if r['exit_reason']=='TAKE' and abs(r['pnl_r']-2)>1e-8:viol.append([n,'TAKE_NOT_PLUS_2R',r['pnl_r']])
        if r['direction']=='LONG' and abs((r['entry']-r['stop'])-2*r['atr20'])>1e-8:viol.append([n,'LONG_STOP_DISTANCE'])
        if r['direction']=='SHORT' and abs((r['stop']-r['entry'])-2*r['atr20'])>1e-8:viol.append([n,'SHORT_STOP_DISTANCE'])
print('AUDIT '+json.dumps({'violations':viol,'passed':len(viol)==0},sort_keys=True))
