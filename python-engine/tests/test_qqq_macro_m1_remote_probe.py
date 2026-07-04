"""Temporary remote probe: fetch free Dukascopy QQQ M1 and print compact coverage.
Delete after the research run.
"""
import json, random, string, io
from datetime import time as dtime
from zoneinfo import ZoneInfo
import pandas as pd
import requests

NY=ZoneInfo('America/New_York')
URL='https://freeserv.dukascopy.com/2.0/index.php'
INSTRUMENT='QQQ.US/USD'
DAILY='https://raw.githubusercontent.com/xunme1/stock_ranking/30bca2c5889b4d1c845b8228b41ef2947bc4a46d/data/raw/daily/QQQ.csv'
EVENTS=[('CPI','2026-02-13','2026-02-20'),('GDP','2026-02-20','2026-03-11'),('CPI','2026-03-11','2026-03-18'),('FOMC','2026-03-18','2026-04-10'),('CPI','2026-04-10','2026-04-29'),('FOMC','2026-04-29','2026-04-30'),('GDP','2026-04-30','2026-05-12'),('CPI','2026-05-12','2026-06-10'),('CPI','2026-06-10','2026-06-17'),('FOMC','2026-06-17',None)]

def emit(tag,obj): print(tag+' '+json.dumps(obj,default=str,sort_keys=True))

def daily_data():
 r=requests.get(DAILY,timeout=60); r.raise_for_status(); d=pd.read_csv(io.StringIO(r.text)); mp={str(c).lower():c for c in d.columns}; dc=mp.get('date',d.columns[0]); ren={dc:'date'}
 for n in ('open','high','low','close'): ren[mp[n]]=n
 d=d.rename(columns=ren); d['date']=pd.to_datetime(d['date'],errors='coerce').dt.tz_localize(None)
 for c in ('open','high','low','close'): d[c]=pd.to_numeric(d[c],errors='coerce')
 d=d.dropna(subset=['date','open','high','low','close']).sort_values('date').reset_index(drop=True)
 pc=d.close.shift(1); tr=pd.concat([d.high-d.low,(d.high-pc).abs(),(d.low-pc).abs()],axis=1).max(axis=1); atr=pd.Series(index=d.index,dtype=float); atr.iloc[19]=tr.iloc[:20].mean()
 for i in range(20,len(d)): atr.iloc[i]=((atr.iloc[i-1]*19)+tr.iloc[i])/20
 d['atr20']=atr; return d

def fetch(side,start,end):
 cursor=int(pd.Timestamp(start,tz='UTC').timestamp()*1000); endms=int(pd.Timestamp(end,tz='UTC').timestamp()*1000); rows=[]; first=True
 for loop in range(40):
  cb='_callbacks____'+''.join(random.choices(string.ascii_letters+string.digits,k=9)); p={'path':'chart/json3','splits':'true','stocks':'true','time_direction':'N','jsonp':cb,'last_update':str(cursor),'offer_side':side,'instrument':INSTRUMENT,'interval':'1MIN','limit':'30000'}; h={'User-Agent':'Mozilla/5.0 Chrome/135 Safari/537.36','Referer':'https://freeserv.dukascopy.com/2.0/?path=chart/index'}
  r=requests.get(URL,params=p,headers=h,timeout=120); r.raise_for_status(); txt=r.text; pre=cb+'('; suf=');'
  if not(txt.startswith(pre) and txt.endswith(suf)): raise RuntimeError('bad response '+txt[:160])
  batch=json.loads(txt[len(pre):-len(suf)])
  if not first and batch and batch[0][0]==cursor: batch=batch[1:]
  if not batch: break
  done=False
  for row in batch:
   if row[0]>endms: done=True; break
   rows.append(row); cursor=int(row[0])
  if done or cursor>=endms: break
  first=False
 df=pd.DataFrame(rows,columns=['timestamp','open','high','low','close','volume'])
 if df.empty:return df
 df['timestamp']=pd.to_datetime(df.timestamp,unit='ms',utc=True); et=df.timestamp.dt.tz_convert(NY); t=et.dt.time; keep=(et.dt.weekday<5)&(t>=dtime(9,30))&(t<dtime(16,0)); df=df.loc[keep].copy(); df['et']=et.loc[keep]; df['date']=df.et.dt.tz_localize(None).dt.normalize(); return df.sort_values('timestamp').drop_duplicates('timestamp').reset_index(drop=True)

def quotes(b,a):
 b=b.rename(columns={c:'bid_'+c for c in ('open','high','low','close','volume')}); a=a.rename(columns={c:'ask_'+c for c in ('open','high','low','close','volume')}); q=pd.merge(b.drop(columns=['et'],errors='ignore'),a.drop(columns=['et'],errors='ignore'),on=['timestamp','date'],how='inner'); q['et']=q.timestamp.dt.tz_convert(NY); return q.sort_values('timestamp').reset_index(drop=True)

def simulate(d,q,ev):
 typ,d0,nm=ev; d0=pd.Timestamp(d0); r=d[d.date==d0].iloc[0]; atr=float(r.atr20); eh=float(r.high); el=float(r.low); buy=eh+.2*atr; sell=el-.2*atr; fut=d[d.date>d0].date.tolist(); d1=fut[0]; nxt=pd.Timestamp(nm) if nm else None
 base={'event':typ,'d0':str(d0.date()),'d1':str(d1.date()),'eh':eh,'el':el,'atr20':atr,'buy':buy,'sell':sell}
 if nxt is not None and d1==nxt:return {**base,'status':'NO_TRADE_NEXT_MACRO_D1'}
 day=q[q.date==d1]; entry=None
 for _,x in day.iterrows():
  bg=x.ask_open>=buy; sg=x.bid_open<=sell; bh=x.ask_high>=buy; sh=x.bid_low<=sell
  if bg and sg:return {**base,'status':'AMBIGUOUS_BOTH_GAP','minute':x.et}
  if bg:entry=('LONG',float(x.ask_open),x.et,'GAP_OPEN');break
  if sg:entry=('SHORT',float(x.bid_open),x.et,'GAP_OPEN');break
  if bh and sh:return {**base,'status':'AMBIGUOUS_BOTH_SAME_M1','minute':x.et}
  if bh:entry=('LONG',buy,x.et,'TRIGGER');break
  if sh:entry=('SHORT',sell,x.et,'TRIGGER');break
 if entry is None:return {**base,'status':'NO_TRIGGER_D1'}
 direction,ep,ts,fill=entry; risk=2*atr; stop=ep-risk if direction=='LONG' else ep+risk; take=ep+2*risk if direction=='LONG' else ep-2*risk; seven=fut[6]; force=seven; freason='TIME_STOP'
 if nxt is not None:
  prior=d[d.date<nxt].date.iloc[-1]
  if prior<force:force=prior;freason='MACRO_SHIELD'
 scan=q[(q.timestamp>=pd.Timestamp(ts).tz_convert('UTC'))&(q.date<=force)]; mae=0.;mfe=0.;xp=None;xt=None;why=None
 for _,x in scan.iterrows():
  if direction=='LONG':
   mae=min(mae,(float(x.bid_low)-ep)/ep*100);mfe=max(mfe,(float(x.bid_high)-ep)/ep*100);sl=float(x.bid_low)<=stop;tp=float(x.bid_high)>=take
  else:
   mae=min(mae,(ep-float(x.ask_high))/ep*100);mfe=max(mfe,(ep-float(x.ask_low))/ep*100);sl=float(x.ask_high)>=stop;tp=float(x.ask_low)<=take
  if sl and tp:xp=stop;xt=x.et;why='STOP_SAME_M1_CONSERVATIVE';break
  if sl:xp=stop;xt=x.et;why='STOP';break
  if tp:xp=take;xt=x.et;why='TAKE';break
 if xp is None:
  z=scan[scan.date==force].tail(1).iloc[0];xp=float(z.bid_close if direction=='LONG' else z.ask_close);xt=z.et;why=freason
 pct=(xp-ep)/ep*100 if direction=='LONG' else (ep-xp)/ep*100; rr=(xp-ep)/risk if direction=='LONG' else (ep-xp)/risk
 return {**base,'status':'TRADE','direction':direction,'entry':ep,'trigger_minute':ts,'fill':fill,'stop':stop,'take':take,'exit':xp,'exit_minute':xt,'exit_reason':why,'pnl_pct':pct,'pnl_r':rr,'mae_pct':mae,'mfe_pct':mfe,'force_day':str(force.date())}

def test_remote_qqq_m1_probe():
 d=daily_data(); emit('DAILY',{'rows':len(d),'first':d.date.min(),'last':d.date.max()}); b=fetch('B','2026-02-01','2026-06-28'); a=fetch('A','2026-02-01','2026-06-28'); emit('DUKA',{'bid_rows':len(b),'ask_rows':len(a),'bid_first':b.timestamp.min() if len(b) else None,'bid_last':b.timestamp.max() if len(b) else None,'bid_days':b.date.nunique() if len(b) else 0}); q=quotes(b,a); emit('QUOTES',{'rows':len(q),'days':q.date.nunique(),'first':q.timestamp.min(),'last':q.timestamp.max()}); res=[simulate(d,q,e) for e in EVENTS]
 for x in res:emit('M1_EVENT',x)
 tr=[x for x in res if x.get('status')=='TRADE']; eq=0.;peak=0.;mdd=0.
 for x in tr:eq+=x['pnl_r'];peak=max(peak,eq);mdd=min(mdd,eq-peak)
 emit('M1_SUMMARY',{'events':len(res),'trades':len(tr),'wins':sum(x['pnl_r']>0 for x in tr),'losses':sum(x['pnl_r']<0 for x in tr),'sum_r':sum(x['pnl_r'] for x in tr),'sum_pct':sum(x['pnl_pct'] for x in tr),'compound_notional_pct':(pd.Series([1+x['pnl_pct']/100 for x in tr]).prod()-1)*100 if tr else 0,'max_closed_dd_r':mdd,'worst_mae_pct':min([x['mae_pct'] for x in tr],default=0),'statuses':pd.Series([x['status'] for x in res]).value_counts().to_dict(),'exit_reasons':pd.Series([x['exit_reason'] for x in tr]).value_counts().to_dict()})
 assert False,'QQQ_M1_REMOTE_PROBE_COMPLETE'
