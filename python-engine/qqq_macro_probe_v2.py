import json,re,urllib.parse,urllib.request
from html.parser import HTMLParser
UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135 Safari/537.36'
def fetch(url,params=None):
 if params:url+=('&' if '?' in url else '?')+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/json;q=0.9,*/*;q=0.8'})
 with urllib.request.urlopen(req,timeout=120) as r:return r.read().decode('utf-8',errors='replace')
class L(HTMLParser):
 def __init__(self):super().__init__();self.cur=None;self.txt=[];self.links=[]
 def handle_starttag(self,tag,attrs):
  if tag=='a':self.cur=dict(attrs).get('href');self.txt=[]
 def handle_data(self,data):
  if self.cur is not None:self.txt.append(data)
 def handle_endtag(self,tag):
  if tag=='a' and self.cur is not None:self.links.append((self.cur,' '.join(''.join(self.txt).split())));self.cur=None;self.txt=[]
# Nasdaq full
try:
 j=json.loads(fetch('https://api.nasdaq.com/api/quote/QQQ/historical',{'assetclass':'etf','fromdate':'2015-01-01','todate':'2026-06-26','limit':'5000'}));d=j.get('data') or {};rows=((d.get('tradesTable') or {}).get('rows') or []);print('NASDAQ_FULL',j.get('status'),'total',d.get('totalRecords'),'rows',len(rows),'first',rows[-1] if rows else None,'last',rows[0] if rows else None)
except Exception as e:print('NASDAQ_FULL_ERR',type(e).__name__,str(e))
# Jina BLS
for y in [2016,2019,2020,2024,2025,2026]:
 for scheme in ['https','http']:
  try:
   url=f'https://r.jina.ai/{scheme}://www.bls.gov/schedule/{y}/home.htm';x=fetch(url);lines=x.splitlines();hits=[]
   for i,line in enumerate(lines):
    if 'Consumer Price Index for' in line:
     hits.append(lines[max(0,i-5):i+2])
   print('JINA_BLS',y,scheme,'len',len(x),'hits',len(hits),'sample',hits[:2]);break
  except Exception as e:print('JINA_BLS_ERR',y,scheme,type(e).__name__,str(e))
# BEA corrected filter
try:
 for y in [2016,2019,2024]:
  q=fetch('https://www.bea.gov/news/archive',{'field_related_product_target_id':'451','created_1':str(y)});lp=L();lp.feed(q);links=[(h,t) for h,t in lp.links if h and '/news/' in h and ('gross domestic product' in t.lower() or 'gross-domestic-product' in h.lower())];print('BEA2',y,'len',len(q),'links',len(links),'sample',links[:20])
except Exception as e:print('BEA2_ERR',type(e).__name__,str(e))
