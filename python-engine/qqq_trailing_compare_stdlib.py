import csv, io, json, math, urllib.request
from datetime import datetime

URL='https://raw.githubusercontent.com/xunme1/stock_ranking/30bca2c5889b4d1c845b8228b41ef2947bc4a46d/data/raw/daily/QQQ.csv'
EVENTS=[
('CPI','2024-07-11'),('GDP','2024-07-25'),('FOMC','2024-07-31'),('CPI','2024-08-14'),('CPI','2024-09-11'),('FOMC','2024-09-18'),('CPI','2024-10-10'),('GDP','2024-10-30'),('FOMC','2024-11-07'),('CPI','2024-11-13'),('CPI','2024-12-11'),('FOMC','2024-12-18'),('CPI','2025-01-15'),('FOMC','2025-01-29'),('GDP','2025-01-30'),('CPI','2025-02-12'),('CPI','2025-03-12'),('FOMC','2025-03-19'),('CPI','2025-04-10'),('GDP','2025-04-30'),('FOMC','2025-05-07'),('CPI','2025-05-13'),('CPI','2025-06-11'),('FOMC','2025-06-18'),('CPI','2025-07-15'),('GDP','2025-07-30'),('FOMC','2025-07-30'),('CPI','2025-08-12'),('CPI','2025-09-11'),('FOMC','2025-09-17'),('FOMC','2025-10-29'),('GDP','2025-10-30'),('FOMC','2025-12-10'),('CPI','2025-12-18'),('CPI','2026-01-13'),('FOMC','2026-01-28'),('CPI','2026-02-13'),('CPI','2026-03-11'),('FOMC','2026-03-18'),('CPI','2026-04-10'),('FOMC','2026-04-29'),('GDP','2026-04-30'),('CPI','2026-05-12'),('CPI','2026-06-10'),('FOMC','2026-06-17')]
EVENTS=sorted(set(EVENTS),key=lambda x:x[1])
raw=urllib.request.urlopen(URL,timeout=60).read().decode('utf-8-sig')
rows=[]
for r in csv.DictReader(io.StringIO(raw)):
    rows.append({'date':datetime.strptime(r['date'],'%Y-%m-%d').date(),'open':float(r['open']),'high':float(r['high']),'low':float(r['low']),'close':float(r['close'])})
rows.sort(key=lambda x:x['date']); idx={r['date']:i for i,r in enumerate(rows)}
trs=[]
for i,r in enumerate(rows):
    pc=rows[i-1]['close'] if i else r['close']
    trs.append(max(r['high']-r['low'],abs(r['high']-pc),abs(r['low']-pc)))
for i,r in enumerate(rows): r['atr20']=sum(trs[i-19:i+1])/20 if i>=19 else None

def next_macro(d0):
    z=[datetime.strptime(d,'%Y-%m-%d').date() for _,d in EVENTS if datetime.strptime(d,'%Y-%m-%d').date()>d0]
    return min(z) if z else None

def entry(typ,ds):
    d0=datetime.strptime(ds,'%Y-%m-%d').date()
    if d0 not in idx:return None
    i=idx[d0];r=rows[i]
    if r['atr20'] is None or i+1>=len(rows):return None
    d1=rows[i+1];nxt=next_macro(d0)
    if nxt and d1['date']==nxt:return {'status':'NO_TRADE'}
    atr=r['atr20'];buy=r['high']+.2*atr;sell=r['low']-.2*atr
    bg=d1['open']>=buy;sg=d1['open']<=sell;bh=d1['high']>=buy;sh=d1['low']<=sell
    if bg and sg or (bh and sh and not bg and not sg):return {'status':'AMBIG'}
    if bg:direction='LONG';ep=d1['open']
    elif sg:direction='SHORT';ep=d1['open']
    elif bh:direction='LONG';ep=buy
    elif sh:direction='SHORT';ep=sell
    else:return {'status':'NO_TRIGGER'}
    return {'status':'ENTRY','event':typ,'d0':d0,'d1':d1['date'],'direction':direction,'entry':ep,'atr':atr}

def force_day(ent):
    start=idx[ent['d1']]; time_day=rows[min(start+6,len(rows)-1)]['date'];nxt=next_macro(ent['d0']);force=time_day;reason='TIME'
    if nxt:
        j=max(i for i,r in enumerate(rows) if r['date']<nxt);macro=rows[j]['date']
        if macro<force:force=macro;reason='MACRO'
    return force,reason

def baseline(ent):
    ep,atr,di=ent['entry'],ent['atr'],ent['direction'];risk=2*atr;stop=ep-risk if di=='LONG' else ep+risk;take=ep+2*risk if di=='LONG' else ep-2*risk;fd,fr=force_day(ent);mae=0;mfe=0
    for x in rows[idx[ent['d1']]:idx[fd]+1]:
        if di=='LONG':mae=min(mae,(x['low']-ep)/risk);mfe=max(mfe,(x['high']-ep)/risk);sl=x['low']<=stop;tp=x['high']>=take
        else:mae=min(mae,(ep-x['high'])/risk);mfe=max(mfe,(ep-x['low'])/risk);sl=x['high']>=stop;tp=x['low']<=take
        if sl:xp=stop;why='STOP';break
        if tp:xp=take;why='TAKE';break
    else:xp=rows[idx[fd]]['close'];why=fr
    rr=(xp-ep)/risk if di=='LONG' else (ep-xp)/risk
    return {'pnl_r':rr,'mae_r':mae,'mfe_r':mfe,'reason':why}

def trailing(ent):
    ep,atr,di=ent['entry'],ent['atr'],ent['direction'];risk=2*atr;hard=ep-risk if di=='LONG' else ep+risk;plus1=ep+risk if di=='LONG' else ep-risk;fd,fr=force_day(ent);armed=False;active=False;activation=None;extreme=None;trail=None;mae=0;mfe=0
    for x in rows[idx[ent['d1']]:idx[fd]+1]:
        if di=='LONG':
            mae=min(mae,(x['low']-ep)/risk);mfe=max(mfe,(x['high']-ep)/risk)
            if x['low']<=hard:xp=hard;why='HARD_STOP';break
            if active:
                if x['low']<=trail:xp=trail;why='ATR_TRAIL';break
                extreme=max(extreme,x['high']);trail=max(trail,extreme-2*atr)
            elif x['high']>=plus1:armed=True;activation=x['date'];extreme=x['high'];trail=extreme-2*atr
            if armed and x['date']>activation:active=True
        else:
            mae=min(mae,(ep-x['high'])/risk);mfe=max(mfe,(ep-x['low'])/risk)
            if x['high']>=hard:xp=hard;why='HARD_STOP';break
            if active:
                if x['high']>=trail:xp=trail;why='ATR_TRAIL';break
                extreme=min(extreme,x['low']);trail=min(trail,extreme+2*atr)
            elif x['low']<=plus1:armed=True;activation=x['date'];extreme=x['low'];trail=extreme+2*atr
            if armed and x['date']>activation:active=True
    else:xp=rows[idx[fd]]['close'];why=fr
    rr=(xp-ep)/risk if di=='LONG' else (ep-xp)/risk
    return {'pnl_r':rr,'mae_r':mae,'mfe_r':mfe,'reason':why,'armed':armed}

def metrics(ts):
    rs=[t['pnl_r'] for t in ts];wins=[r for r in rs if r>0];losses=[r for r in rs if r<0];eq=0;peak=0;mdd=0
    for r in rs:eq+=r;peak=max(peak,eq);mdd=min(mdd,eq-peak)
    gw=sum(wins);gl=-sum(losses)
    return {'trades':len(rs),'wins':len(wins),'losses':len(losses),'win_rate':len(wins)/len(rs)*100,'total_r':sum(rs),'expectancy_r':sum(rs)/len(rs),'pf':gw/gl if gl else None,'max_dd_r':mdd,'avg_win_r':sum(wins)/len(wins),'avg_loss_r':sum(losses)/len(losses),'worst_mae_r':min(t['mae_r'] for t in ts),'avg_mfe_r':sum(t['mfe_r'] for t in ts)/len(ts),'exit_reasons':{k:sum(1 for t in ts if t['reason']==k) for k in sorted(set(t['reason'] for t in ts))}}
entries=[];statuses=[]
for typ,ds in EVENTS:
    e=entry(typ,ds)
    if e:statuses.append(e['status'])
    if e and e['status']=='ENTRY':entries.append(e)
base=[baseline(e) for e in entries];trail=[trailing(e) for e in entries]
print('SAMPLE '+json.dumps({'events':len(EVENTS),'entries':len(entries),'statuses':{k:statuses.count(k) for k in sorted(set(statuses))},'first':str(entries[0]['d0']),'last':str(entries[-1]['d0'])},sort_keys=True))
print('BASELINE '+json.dumps(metrics(base),sort_keys=True))
print('TRAILING '+json.dumps(metrics(trail),sort_keys=True))
print('DELTA '+json.dumps({'total_r':metrics(trail)['total_r']-metrics(base)['total_r'],'expectancy_r':metrics(trail)['expectancy_r']-metrics(base)['expectancy_r'],'pf':metrics(trail)['pf']-metrics(base)['pf'],'max_dd_r':metrics(trail)['max_dd_r']-metrics(base)['max_dd_r'],'armed':sum(t['armed'] for t in trail)},sort_keys=True))
