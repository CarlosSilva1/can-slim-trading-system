import csv, io, json, urllib.request, urllib.error, calendar
from datetime import datetime, timezone
from functools import reduce

STOOQ_URLS=[
    'https://stooq.com/q/d/l/?s=qqq.us&i=d&d1=20160101&d2=20260626',
    'https://stooq.com/q/d/l/?s=qqq&i=d&d1=20160101&d2=20260626',
]
YAHOO_URL='https://query1.finance.yahoo.com/v8/finance/chart/QQQ?period1={p1}&period2={p2}&interval=1d&events=history&includeAdjustedClose=true'

CPI=['2016-01-20','2016-02-19','2016-03-16','2016-04-14','2016-05-17','2016-06-16','2016-07-15','2016-08-16','2016-09-16','2016-10-18','2016-11-17','2016-12-15','2017-01-18','2017-02-15','2017-03-15','2017-04-14','2017-05-12','2017-06-14','2017-07-14','2017-08-11','2017-09-14','2017-10-13','2017-11-15','2017-12-13','2018-01-12','2018-02-14','2018-03-13','2018-04-11','2018-05-10','2018-06-12','2018-07-12','2018-08-10','2018-09-13','2018-10-11','2018-11-14','2018-12-12','2019-01-11','2019-02-13','2019-03-12','2019-04-10','2019-05-10','2019-06-12','2019-07-11','2019-08-13','2019-09-12','2019-10-10','2019-11-13','2019-12-11','2020-01-14','2020-02-13','2020-03-11','2020-04-10','2020-05-12','2020-06-10','2020-07-14','2020-08-12','2020-09-11','2020-10-13','2020-11-12','2020-12-10','2021-01-13','2021-02-10','2021-03-10','2021-04-13','2021-05-12','2021-06-10','2021-07-13','2021-08-11','2021-09-14','2021-10-13','2021-11-10','2021-12-10','2022-01-12','2022-02-10','2022-03-10','2022-04-12','2022-05-11','2022-06-10','2022-07-13','2022-08-10','2022-09-13','2022-10-13','2022-11-10','2022-12-13','2023-01-12','2023-02-14','2023-03-14','2023-04-12','2023-05-10','2023-06-13','2023-07-12','2023-08-10','2023-09-13','2023-10-12','2023-11-14','2023-12-12','2024-01-11','2024-02-13','2024-03-12','2024-04-10','2024-05-15','2024-06-12','2024-07-11','2024-08-14','2024-09-11','2024-10-10','2024-11-13','2024-12-11','2025-01-15','2025-02-12','2025-03-12','2025-04-10','2025-05-13','2025-06-11','2025-07-15','2025-08-12','2025-09-11','2025-12-18','2026-01-13','2026-02-13','2026-03-11','2026-04-10','2026-05-12','2026-06-10']
FOMC=['2016-01-27','2016-03-16','2016-04-27','2016-06-15','2016-07-27','2016-09-21','2016-11-02','2016-12-14','2017-02-01','2017-03-15','2017-05-03','2017-06-14','2017-07-26','2017-09-20','2017-11-01','2017-12-13','2018-01-31','2018-03-21','2018-05-02','2018-06-13','2018-08-01','2018-09-26','2018-11-08','2018-12-19','2019-01-30','2019-03-20','2019-05-01','2019-06-19','2019-07-31','2019-09-18','2019-10-30','2019-12-11','2020-01-29','2020-03-03','2020-03-15','2020-04-29','2020-06-10','2020-07-29','2020-09-16','2020-11-05','2020-12-16','2021-01-27','2021-03-17','2021-04-28','2021-06-16','2021-07-28','2021-09-22','2021-11-03','2021-12-15','2022-01-26','2022-03-16','2022-05-04','2022-06-15','2022-07-27','2022-09-21','2022-11-02','2022-12-14','2023-02-01','2023-03-22','2023-05-03','2023-06-14','2023-07-26','2023-09-20','2023-11-01','2023-12-13','2024-01-31','2024-03-20','2024-05-01','2024-06-12','2024-07-31','2024-09-18','2024-11-07','2024-12-18','2025-01-29','2025-03-19','2025-05-07','2025-06-18','2025-07-30','2025-09-17','2025-10-29','2025-12-10','2026-01-28','2026-03-18','2026-04-29','2026-06-17']
GDP=['2016-01-29','2016-04-28','2016-07-29','2016-10-28','2017-01-27','2017-04-28','2017-07-28','2017-10-27','2018-01-26','2018-04-27','2018-07-27','2018-10-26','2019-01-30','2019-04-26','2019-07-26','2019-10-30','2020-01-30','2020-04-29','2020-07-30','2020-10-29','2021-01-28','2021-04-29','2021-07-29','2021-10-28','2022-01-27','2022-04-28','2022-07-28','2022-10-27','2023-01-26','2023-04-27','2023-07-27','2023-10-26','2024-01-25','2024-04-25','2024-07-25','2024-10-30','2025-01-30','2025-04-30','2025-07-30','2025-10-30','2026-02-20','2026-04-30']

def emit(tag,obj): print(tag+' '+json.dumps(obj,sort_keys=True,default=str))

def load_stooq(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
    raw=urllib.request.urlopen(req,timeout=60).read().decode('utf-8-sig')
    out=[]
    for r in csv.DictReader(io.StringIO(raw)):
        if not r.get('Date') or not r.get('Open'): continue
        out.append({'date':datetime.strptime(r['Date'],'%Y-%m-%d').date(),'open':float(r['Open']),'high':float(r['High']),'low':float(r['Low']),'close':float(r['Close']),'volume':float(r['Volume'])})
    return out

def load_yahoo():
    p1=calendar.timegm(datetime(2016,1,1,tzinfo=timezone.utc).timetuple())
    p2=calendar.timegm(datetime(2026,6,27,tzinfo=timezone.utc).timetuple())
    req=urllib.request.Request(YAHOO_URL.format(p1=p1,p2=p2),headers={'User-Agent':'Mozilla/5.0'})
    data=json.loads(urllib.request.urlopen(req,timeout=60).read().decode('utf-8'))['chart']['result'][0]
    q=data['indicators']['quote'][0]; adj=data['indicators'].get('adjclose',[{}])[0].get('adjclose') or q['close']
    out=[]
    for ts,o,h,l,c,ac,v in zip(data['timestamp'],q['open'],q['high'],q['low'],q['close'],adj,q['volume']):
        if None in (o,h,l,c,ac): continue
        factor=ac/c if c else 1.0
        out.append({'date':datetime.fromtimestamp(ts,timezone.utc).date(),'open':o*factor,'high':h*factor,'low':l*factor,'close':ac,'volume':float(v or 0)})
    return out

def load_prices():
    errors=[]
    for url in STOOQ_URLS:
        try:
            r=load_stooq(url)
            if len(r)>2000: return 'Stooq adjusted daily OHLC', r
            errors.append(f'{url}: only {len(r)} rows')
        except Exception as e:
            errors.append(f'{url}: {type(e).__name__}: {e}')
    try:
        r=load_yahoo()
        if len(r)>2000: return 'Yahoo Finance chart API adjusted OHLC fallback after Stooq errors: '+ ' | '.join(errors), r
        raise RuntimeError(f'Yahoo returned only {len(r)} rows')
    except Exception as e:
        raise RuntimeError('All price sources failed: '+ ' | '.join(errors+[f'Yahoo: {type(e).__name__}: {e}']))

source,rows=load_prices()
rows.sort(key=lambda x:x['date']); idx={r['date']:i for i,r in enumerate(rows)}
trs=[]
for i,r in enumerate(rows):
    pc=rows[i-1]['close'] if i else r['close']
    trs.append(max(r['high']-r['low'],abs(r['high']-pc),abs(r['low']-pc)))
ema=None; alpha=2/(21+1)
for i,r in enumerate(rows):
    r['atr20']=sum(trs[i-19:i+1])/20 if i>=19 else None
    ema=r['close'] if ema is None else alpha*r['close']+(1-alpha)*ema
    r['ema21']=ema

bydate={}
for label,arr in [('CPI',CPI),('FOMC',FOMC),('GDP',GDP)]:
    for ds in arr:
        d=datetime.strptime(ds,'%Y-%m-%d').date(); bydate.setdefault(d,[]).append(label)
all_event_dates=sorted(d for d in bydate if rows[0]['date']<=d<=rows[-1]['date'])

def next_macro(d0):
    z=[d for d in all_event_dates if d>d0]
    return min(z) if z else None

def entry_for(d0):
    if d0 not in idx: return {'status':'NO_PRICE_D0','d0':d0,'event':'+'.join(bydate[d0])}
    i=idx[d0]; r=rows[i]
    if r['atr20'] is None or i+1>=len(rows): return {'status':'NO_ATR_OR_FUTURE','d0':d0,'event':'+'.join(bydate[d0])}
    d1=rows[i+1]; nxt=next_macro(d0)
    rec={'event':'+'.join(bydate[d0]),'d0':d0,'d1':d1['date'],'eh':r['high'],'el':r['low'],'atr':r['atr20'],'buy':r['high']+.2*r['atr20'],'sell':r['low']-.2*r['atr20']}
    if nxt and d1['date']==nxt: rec['status']='NO_TRADE_NEXT_MACRO_D1'; return rec
    bg=d1['open']>=rec['buy']; sg=d1['open']<=rec['sell']; bh=d1['high']>=rec['buy']; sh=d1['low']<=rec['sell']
    if (bg and sg) or (bh and sh and not bg and not sg): rec['status']='AMBIGUOUS_D1'; return rec
    if bg: di='LONG'; ep=d1['open']; fill='GAP_OPEN'
    elif sg: di='SHORT'; ep=d1['open']; fill='GAP_OPEN'
    elif bh: di='LONG'; ep=rec['buy']; fill='TRIGGER'
    elif sh: di='SHORT'; ep=rec['sell']; fill='TRIGGER'
    else: rec['status']='NO_TRIGGER_D1'; return rec
    rec.update({'status':'ENTRY','direction':di,'entry':ep,'fill':fill}); return rec

def force_day(ent):
    start=idx[ent['d1']]; force=rows[min(start+6,len(rows)-1)]['date']; reason='TIME_STOP'; nxt=next_macro(ent['d0'])
    if nxt:
        prior=max(r['date'] for r in rows if r['date']<nxt)
        if prior<force: force=prior; reason='MACRO_SHIELD'
    return force,reason

def baseline(ent):
    ep=ent['entry']; atr=ent['atr']; di=ent['direction']; risk=2*atr; stop=ep-risk if di=='LONG' else ep+risk; take=ep+2*risk if di=='LONG' else ep-2*risk; force,fr=force_day(ent); mae=mfe=0.0
    for x in rows[idx[ent['d1']]:idx[force]+1]:
        if di=='LONG':
            mae=min(mae,(x['low']-ep)/risk); mfe=max(mfe,(x['high']-ep)/risk); sl=x['low']<=stop; tp=x['high']>=take
        else:
            mae=min(mae,(ep-x['high'])/risk); mfe=max(mfe,(ep-x['low'])/risk); sl=x['high']>=stop; tp=x['low']<=take
        if sl and tp: xp=stop; why='STOP_SAME_BAR'; xd=x['date']; break
        if sl: xp=stop; why='STOP'; xd=x['date']; break
        if tp: xp=take; why='TAKE'; xd=x['date']; break
    else: xp=rows[idx[force]]['close']; why=fr; xd=force
    rr=(xp-ep)/risk if di=='LONG' else (ep-xp)/risk; pct=(xp-ep)/ep*100 if di=='LONG' else (ep-xp)/ep*100
    return {**ent,'exit':xp,'exit_date':xd,'exit_reason':why,'pnl_r':rr,'pnl_pct':pct,'mae_r':mae,'mfe_r':mfe}

def ema21(ent):
    ep=ent['entry']; atr=ent['atr']; di=ent['direction']; risk=2*atr; stop=ep-risk if di=='LONG' else ep+risk; plus1=ep+risk if di=='LONG' else ep-risk; force,fr=force_day(ent); mae=mfe=0.0; armed=False; sig=None
    i=idx[ent['d1']]; force_i=idx[force]
    while i<=force_i:
        x=rows[i]
        if di=='LONG':
            mae=min(mae,(x['low']-ep)/risk); mfe=max(mfe,(x['high']-ep)/risk)
            if x['low']<=stop: xp=stop; why='STOP'; xd=x['date']; break
            if not armed and x['high']>=plus1: armed=True
            if armed and x['close']<x['ema21']:
                sig=x['date']
                if i+1<=force_i: xp=rows[i+1]['open']; xd=rows[i+1]['date']; why='EMA21_NEXT_OPEN'; break
                xp=x['close']; xd=x['date']; why=fr; break
        else:
            mae=min(mae,(ep-x['high'])/risk); mfe=max(mfe,(ep-x['low'])/risk)
            if x['high']>=stop: xp=stop; why='STOP'; xd=x['date']; break
            if not armed and x['low']<=plus1: armed=True
            if armed and x['close']>x['ema21']:
                sig=x['date']
                if i+1<=force_i: xp=rows[i+1]['open']; xd=rows[i+1]['date']; why='EMA21_NEXT_OPEN'; break
                xp=x['close']; xd=x['date']; why=fr; break
        i+=1
    else: xp=rows[force_i]['close']; xd=force; why=fr
    rr=(xp-ep)/risk if di=='LONG' else (ep-xp)/risk; pct=(xp-ep)/ep*100 if di=='LONG' else (ep-xp)/ep*100
    return {**ent,'exit':xp,'exit_date':xd,'exit_reason':why,'pnl_r':rr,'pnl_pct':pct,'mae_r':mae,'mfe_r':mfe,'ema_armed':armed,'ema_signal_date':sig}

def metrics(trades):
    if not trades: return {'trades':0}
    wins=[t for t in trades if t['pnl_r']>0]; losses=[t for t in trades if t['pnl_r']<0]; eq=peak=mdd=0.0
    for t in trades:
        eq+=t['pnl_r']; peak=max(peak,eq); mdd=min(mdd,eq-peak)
    gw=sum(t['pnl_r'] for t in wins); gl=-sum(t['pnl_r'] for t in losses)
    return {'trades':len(trades),'wins':len(wins),'losses':len(losses),'win_rate_pct':len(wins)/len(trades)*100,'total_r':sum(t['pnl_r'] for t in trades),'expectancy_r':sum(t['pnl_r'] for t in trades)/len(trades),'profit_factor':gw/gl if gl else None,'max_closed_dd_r':mdd,'avg_win_r':gw/len(wins) if wins else 0,'avg_loss_r':-gl/len(losses) if losses else 0,'sum_trade_pct':sum(t['pnl_pct'] for t in trades),'compound_notional_pct':(reduce(lambda a,t:a*(1+t['pnl_pct']/100),trades,1)-1)*100,'exit_reasons':{k:sum(1 for t in trades if t['exit_reason']==k) for k in sorted(set(t['exit_reason'] for t in trades))}}

def year_bucket(d): return str(d.year)
def half_bucket(d): return f'{d.year}H{1 if d.month<=6 else 2}'
def in_period(d,start,end): return datetime.strptime(start,'%Y-%m-%d').date()<=d<=datetime.strptime(end,'%Y-%m-%d').date()

entries=[]; statuses={}
for d0 in all_event_dates:
    e=entry_for(d0); statuses[e['status']]=statuses.get(e['status'],0)+1
    if e['status']=='ENTRY': entries.append(e)
base=[baseline(e) for e in entries]; ema=[ema21(e) for e in entries]
mb_all=metrics(base); me_all=metrics(ema)

emit('DATA_COVERAGE',{'price_source':source,'first':rows[0]['date'],'last':rows[-1]['date'],'bars':len(rows),'event_dates':len(all_event_dates),'entries':len(entries),'statuses':statuses})
emit('RULES',{'baseline':'0.20 ATR20 buffer / D+1 OCO / hard stop 2ATR=1R / take 2R / 7 sessions / Macro Shield','ema21':'same entry and hard stop; after +1R, exit next open after D1 close crosses EMA21; no fixed 2R take','atr':'SMA20 True Range','ambiguity':'same-day both OCO sides touched without gap -> no trade'})
emit('BASELINE_ALL',mb_all); emit('EMA21_ALL',me_all); emit('DELTA_ALL',{'total_r':me_all['total_r']-mb_all['total_r'],'expectancy_r':me_all['expectancy_r']-mb_all['expectancy_r'],'pf_delta':(me_all['profit_factor'] or 0)-(mb_all['profit_factor'] or 0),'max_dd_delta':me_all['max_closed_dd_r']-mb_all['max_closed_dd_r'],'ema_armed':sum(1 for t in ema if t.get('ema_armed')),'ema_actual_exits':sum(1 for t in ema if t['exit_reason']=='EMA21_NEXT_OPEN')})
for start,end,name in [('2016-01-01','2020-12-31','TRAIN_2016_2020'),('2021-01-01','2026-06-26','OOS_2021_2026'),('2016-01-01','2018-12-31','BLOCK_2016_2018'),('2019-01-01','2021-12-31','BLOCK_2019_2021'),('2022-01-01','2024-12-31','BLOCK_2022_2024'),('2025-01-01','2026-06-26','BLOCK_2025_2026')]:
    b=[t for t in base if in_period(t['d0'],start,end)]; e=[t for t in ema if in_period(t['d0'],start,end)]; mb=metrics(b); me=metrics(e)
    emit('PERIOD_'+name,{'baseline':mb,'ema21':me,'delta_total_r':me.get('total_r',0)-mb.get('total_r',0),'delta_expectancy':me.get('expectancy_r',0)-mb.get('expectancy_r',0),'delta_max_dd':me.get('max_closed_dd_r',0)-mb.get('max_closed_dd_r',0)})
for bucket_func,tag in [(year_bucket,'YEAR'),(half_bucket,'HALF')]:
    for k in sorted(set(bucket_func(t['d0']) for t in base)):
        b=[t for t in base if bucket_func(t['d0'])==k]; e=[t for t in ema if bucket_func(t['d0'])==k]
        mb=metrics(b); me=metrics(e)
        emit(tag+'_'+k,{'trades':len(b),'baseline_total_r':mb['total_r'],'ema21_total_r':me['total_r'],'delta_r':me['total_r']-mb['total_r'],'baseline_pf':mb['profit_factor'],'ema21_pf':me['profit_factor'],'baseline_dd':mb['max_closed_dd_r'],'ema21_dd':me['max_closed_dd_r']})
pairs=[{'d0':b['d0'],'event':b['event'],'baseline_r':b['pnl_r'],'ema21_r':e['pnl_r'],'delta_r':e['pnl_r']-b['pnl_r'],'base_exit':b['exit_reason'],'ema_exit':e['exit_reason'],'ema_armed':e.get('ema_armed')} for b,e in zip(base,ema)]
pairs_sorted=sorted(pairs,key=lambda x:abs(x['delta_r']),reverse=True); emit('TOP_DELTAS',pairs_sorted[:15])
viol=[]
for n,t in enumerate(base,1):
    if t['exit_reason'].startswith('STOP') and abs(t['pnl_r']+1)>1e-8: viol.append([n,'baseline stop not -1R',t['pnl_r']])
    if t['exit_reason']=='TAKE' and abs(t['pnl_r']-2)>1e-8: viol.append([n,'baseline take not +2R',t['pnl_r']])
for n,t in enumerate(ema,1):
    if t['exit_reason'].startswith('STOP') and abs(t['pnl_r']+1)>1e-8: viol.append([n,'ema stop not -1R',t['pnl_r']])
leave_one_max=max([abs((me_all['total_r']-mb_all['total_r'])-p['delta_r']) for p in pairs] or [0])
emit('AUDIT',{'passed':len(viol)==0 and len(base)==len(ema)==len(entries) and rows[0]['date']<=datetime(2016,1,1).date() and rows[-1]['date']>=datetime(2026,6,26).date(),'violations':viol,'paired_trades':len(base)==len(ema)==len(entries),'leave_one_delta_total_r_max_abs':leave_one_max})
emit('VERDICT',{'promote_ema21':me_all['total_r']>mb_all['total_r'] and me_all['expectancy_r']>mb_all['expectancy_r'] and me_all['max_closed_dd_r']>=mb_all['max_closed_dd_r'],'summary':'Promote EMA21 only if it improves Total R and expectancy without worse closed max drawdown; otherwise keep Baseline 2R.'})
