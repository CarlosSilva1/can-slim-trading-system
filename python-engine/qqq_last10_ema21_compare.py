import csv, io, json, urllib.request
from datetime import datetime
from functools import reduce

URL='https://raw.githubusercontent.com/xunme1/stock_ranking/30bca2c5889b4d1c845b8228b41ef2947bc4a46d/data/raw/daily/QQQ.csv'
EVENTS=[('CPI','2026-02-13'),('GDP','2026-02-20'),('CPI','2026-03-11'),('FOMC','2026-03-18'),('CPI','2026-04-10'),('FOMC','2026-04-29'),('GDP','2026-04-30'),('CPI','2026-05-12'),('CPI','2026-06-10'),('FOMC','2026-06-17')]
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
alpha=2/(21+1)
ema=None
for r in rows:
    ema=r['close'] if ema is None else alpha*r['close']+(1-alpha)*ema
    r['ema21']=ema

event_dates=[datetime.strptime(d,'%Y-%m-%d').date() for _,d in EVENTS]
def next_macro(d0):
    z=[d for d in event_dates if d>d0]
    return min(z) if z else None

def get_entries():
    out=[]
    for typ,ds in EVENTS:
        d0=datetime.strptime(ds,'%Y-%m-%d').date();i=idx[d0];r=rows[i];d1=rows[i+1];nxt=next_macro(d0)
        rec={'event':typ,'d0':d0,'d1':d1['date'],'atr':r['atr20'],'buy':r['high']+.2*r['atr20'],'sell':r['low']-.2*r['atr20']}
        if nxt and d1['date']==nxt: rec['status']='NO_TRADE_NEXT_MACRO';out.append(rec);continue
        bg=d1['open']>=rec['buy'];sg=d1['open']<=rec['sell'];bh=d1['high']>=rec['buy'];sh=d1['low']<=rec['sell']
        if (bg and sg) or (bh and sh and not bg and not sg): rec['status']='AMBIG';out.append(rec);continue
        if bg:di='LONG';ep=d1['open'];fill='GAP_OPEN'
        elif sg:di='SHORT';ep=d1['open'];fill='GAP_OPEN'
        elif bh:di='LONG';ep=rec['buy'];fill='TRIGGER'
        elif sh:di='SHORT';ep=rec['sell'];fill='TRIGGER'
        else:rec['status']='NO_TRIGGER';out.append(rec);continue
        rec.update({'status':'ENTRY','direction':di,'entry':ep,'fill':fill})
        out.append(rec)
    return out

def force_day(ent):
    start=idx[ent['d1']];time_day=rows[min(start+6,len(rows)-1)]['date'];nxt=next_macro(ent['d0']);force=time_day;reason='TIME_STOP'
    if nxt:
        prior=max(r['date'] for r in rows if r['date']<nxt)
        if prior<force:force=prior;reason='MACRO_SHIELD'
    return force,reason

def baseline(ent):
    ep=ent['entry'];atr=ent['atr'];di=ent['direction'];risk=2*atr;stop=ep-risk if di=='LONG' else ep+risk;take=ep+2*risk if di=='LONG' else ep-2*risk;force,fr=force_day(ent);mae=0;mfe=0
    for x in rows[idx[ent['d1']]:idx[force]+1]:
        if di=='LONG':mae=min(mae,(x['low']-ep)/ep*100);mfe=max(mfe,(x['high']-ep)/ep*100);sl=x['low']<=stop;tp=x['high']>=take
        else:mae=min(mae,(ep-x['high'])/ep*100);mfe=max(mfe,(ep-x['low'])/ep*100);sl=x['high']>=stop;tp=x['low']<=take
        if sl:xp=stop;why='STOP';xd=x['date'];break
        if tp:xp=take;why='TAKE';xd=x['date'];break
    else:xp=rows[idx[force]]['close'];why=fr;xd=force
    rr=(xp-ep)/risk if di=='LONG' else (ep-xp)/risk
    pct=(xp-ep)/ep*100 if di=='LONG' else (ep-xp)/ep*100
    return {**ent,'exit':xp,'exit_date':xd,'exit_reason':why,'pnl_r':rr,'pnl_pct':pct,'mae_pct':mae,'mfe_pct':mfe}

def ema21(ent):
    ep=ent['entry'];atr=ent['atr'];di=ent['direction'];risk=2*atr;stop=ep-risk if di=='LONG' else ep+risk;plus1=ep+risk if di=='LONG' else ep-risk;force,fr=force_day(ent);mae=0;mfe=0;armed=False;signal_date=None
    start_i=idx[ent['d1']];force_i=idx[force]
    i=start_i
    while i<=force_i:
        x=rows[i]
        if di=='LONG':
            mae=min(mae,(x['low']-ep)/ep*100);mfe=max(mfe,(x['high']-ep)/ep*100)
            if x['low']<=stop:xp=stop;why='STOP';xd=x['date'];break
            if not armed and x['high']>=plus1:armed=True
            # Daily-close EMA21 trailing. Signal on close; exit next open.
            if armed and x['close']<x['ema21']:
                signal_date=x['date']
                if i+1<=force_i:
                    xp=rows[i+1]['open'];xd=rows[i+1]['date'];why='EMA21_NEXT_OPEN';break
                else:
                    xp=x['close'];xd=x['date'];why=fr;break
        else:
            mae=min(mae,(ep-x['high'])/ep*100);mfe=max(mfe,(ep-x['low'])/ep*100)
            if x['high']>=stop:xp=stop;why='STOP';xd=x['date'];break
            if not armed and x['low']<=plus1:armed=True
            if armed and x['close']>x['ema21']:
                signal_date=x['date']
                if i+1<=force_i:
                    xp=rows[i+1]['open'];xd=rows[i+1]['date'];why='EMA21_NEXT_OPEN';break
                else:
                    xp=x['close'];xd=x['date'];why=fr;break
        i+=1
    else:
        xp=rows[force_i]['close'];xd=force;why=fr
    rr=(xp-ep)/risk if di=='LONG' else (ep-xp)/risk
    pct=(xp-ep)/ep*100 if di=='LONG' else (ep-xp)/ep*100
    return {**ent,'exit':xp,'exit_date':xd,'exit_reason':why,'pnl_r':rr,'pnl_pct':pct,'mae_pct':mae,'mfe_pct':mfe,'ema_armed':armed,'ema_signal_date':signal_date}

def metrics(trades):
    wins=[t for t in trades if t['pnl_r']>0];losses=[t for t in trades if t['pnl_r']<0];eq=peak=mdd=0.0
    for t in trades:
        eq+=t['pnl_r'];peak=max(peak,eq);mdd=min(mdd,eq-peak)
    gw=sum(t['pnl_r'] for t in wins);gl=-sum(t['pnl_r'] for t in losses)
    return {'trades':len(trades),'wins':len(wins),'losses':len(losses),'win_rate_pct':len(wins)/len(trades)*100,'total_r':sum(t['pnl_r'] for t in trades),'expectancy_r':sum(t['pnl_r'] for t in trades)/len(trades),'profit_factor':gw/gl if gl else None,'max_closed_dd_r':mdd,'sum_trade_pct':sum(t['pnl_pct'] for t in trades),'compound_notional_pct':(reduce(lambda a,t:a*(1+t['pnl_pct']/100),trades,1)-1)*100,'exit_reasons':{k:sum(1 for t in trades if t['exit_reason']==k) for k in sorted(set(t['exit_reason'] for t in trades))}}
entries=[e for e in get_entries() if e['status']=='ENTRY']
base=[baseline(e) for e in entries]
ema=[ema21(e) for e in entries]
print('RULE '+json.dumps({'ema21':'EMA21 exponential on D1 close','activation':'after intraday price first reaches +1R','signal_long':'D1 close < EMA21','signal_short':'D1 close > EMA21','execution':'next session open','hard_stop':'2 ATR20 remains active','fixed_take':'removed in EMA21 variant','time_stop':'7 sessions','macro_shield':'unchanged'},sort_keys=True))
print('BASELINE '+json.dumps(metrics(base),sort_keys=True))
print('EMA21 '+json.dumps(metrics(ema),sort_keys=True))
for n,(b,e) in enumerate(zip(base,ema),1):print('COMPARE_%02d '%n+json.dumps({'event':b['event'],'d0':str(b['d0']),'direction':b['direction'],'baseline_r':b['pnl_r'],'baseline_exit':b['exit_reason'],'ema21_r':e['pnl_r'],'ema21_exit':e['exit_reason'],'ema_armed':e['ema_armed'],'ema_signal_date':str(e['ema_signal_date']) if e['ema_signal_date'] else None,'delta_r':e['pnl_r']-b['pnl_r']},sort_keys=True))
print('DELTA '+json.dumps({'total_r':metrics(ema)['total_r']-metrics(base)['total_r'],'expectancy_r':metrics(ema)['expectancy_r']-metrics(base)['expectancy_r'],'profit_factor':metrics(ema)['profit_factor']-metrics(base)['profit_factor'],'max_dd_r':metrics(ema)['max_closed_dd_r']-metrics(base)['max_closed_dd_r'],'ema_armed_trades':sum(1 for x in ema if x['ema_armed'])},sort_keys=True))
