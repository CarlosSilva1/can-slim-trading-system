import json, urllib.parse, urllib.request
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/135 Safari/537.36'
def f(params):
 u='https://api.nasdaq.com/api/quote/QQQ/historical?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(u,headers={'User-Agent':UA,'Accept':'application/json, text/plain, */*','Referer':'https://www.nasdaq.com/market-activity/etf/qqq/historical'})
 try:
  with urllib.request.urlopen(req,timeout=90) as r:x=r.read().decode()
  j=json.loads(x);d=j.get('data');rows=((d or {}).get('tradesTable') or {}).get('rows') if isinstance(d,dict) else None
  print('PARAMS',params,'status',j.get('status'),'rows',len(rows) if rows else 0,'sample',rows[:2] if rows else None,'data',str(d)[:500])
 except Exception as e:print('ERR',params,type(e).__name__,str(e))
for p in [
 {'assetclass':'etf','limit':'5000'},
 {'assetclass':'etf','fromdate':'01/01/2025','todate':'06/26/2026','limit':'5000'},
 {'assetclass':'etf','fromdate':'1/1/2025','todate':'6/26/2026','limit':'5000'},
 {'assetclass':'etf','fromdate':'2025-01-01','todate':'2026-06-26','limit':'5000'},
 {'assetclass':'etf','fromdate':'01-01-2025','todate':'06-26-2026','limit':'5000'},
 {'assetclass':'etf','fromdate':'01%2F01%2F2025','todate':'06%2F26%2F2026','limit':'5000'},
 {'assetclass':'etf','limit':'5000','offset':'0'},
 {'assetclass':'etf','limit':'5000','offset':'5000'},
]:f(p)
