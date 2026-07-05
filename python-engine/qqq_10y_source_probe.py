import csv, io, json, re, urllib.parse, urllib.request
from html.parser import HTMLParser

UA='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135 Safari/537.36'
def fetch(url,params=None):
    if params:url += ('&' if '?' in url else '?')+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={'User-Agent':UA})
    with urllib.request.urlopen(req,timeout=90) as r:return r.read().decode('utf-8',errors='replace')

class T(HTMLParser):
    def __init__(self):super().__init__();self.intr=False;self.incell=False;self.cell=[];self.row=[];self.rows=[]
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.intr=True;self.row=[]
        elif self.intr and tag in ('td','th'):self.incell=True;self.cell=[]
    def handle_data(self,data):
        if self.incell:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.incell:self.row.append(' '.join(''.join(self.cell).split()));self.incell=False
        elif tag=='tr' and self.intr:
            if self.row:self.rows.append(self.row)
            self.intr=False
class L(HTMLParser):
    def __init__(self):super().__init__();self.cur=None;self.txt=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        if tag=='a':self.cur=dict(attrs).get('href');self.txt=[]
    def handle_data(self,data):
        if self.cur is not None:self.txt.append(data)
    def handle_endtag(self,tag):
        if tag=='a' and self.cur is not None:self.links.append((self.cur,' '.join(''.join(self.txt).split())));self.cur=None;self.txt=[]
class S(HTMLParser):
    def __init__(self):super().__init__();self.sel=None;self.opt=False;self.val=None;self.txt=[];self.options=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='select':self.sel=a.get('name')
        elif tag=='option' and self.sel:self.opt=True;self.val=a.get('value');self.txt=[]
    def handle_data(self,data):
        if self.opt:self.txt.append(data)
    def handle_endtag(self,tag):
        if tag=='option' and self.opt:self.options.append((self.sel,self.val,' '.join(''.join(self.txt).split())));self.opt=False
        elif tag=='select':self.sel=None

# Stooq
for symbol in ['qqq.us','qqq']:
    try:
        u=f'https://stooq.com/q/d/l/?s={symbol}&i=d&d1=20150101&d2=20260626'
        x=fetch(u);lines=x.splitlines();print('STOOQ',symbol,'lines',len(lines),'head',lines[:3],'tail',lines[-3:])
    except Exception as e:print('STOOQ_ERR',symbol,type(e).__name__,str(e))

# Nasdaq API
try:
    x=fetch('https://api.nasdaq.com/api/quote/QQQ/historical',{'assetclass':'etf','fromdate':'01/01/2015','limit':'5000'})
    j=json.loads(x);print('NASDAQ_KEYS',j.keys());print('NASDAQ_STATUS',j.get('status'));data=j.get('data');print('NASDAQ_DATA_KEYS',data.keys() if isinstance(data,dict) else type(data));print('NASDAQ_SAMPLE',str(data)[:1500])
except Exception as e:print('NASDAQ_ERR',type(e).__name__,str(e))

# BLS sample/all counts
for y in [2016,2019,2020,2024,2025,2026]:
    try:
        html=fetch(f'https://www.bls.gov/schedule/{y}/home.htm');p=T();p.feed(html);rows=[r for r in p.rows if any(c.strip()=='Consumer Price Index' for c in r)];print('BLS',y,'count',len(rows),'sample',rows[:3])
    except Exception as e:print('BLS_ERR',y,type(e).__name__,str(e))

# Fed statement links
for label,url in [('current','https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm')]+[(str(y),f'https://www.federalreserve.gov/monetarypolicy/fomchistorical{y}.htm') for y in range(2016,2021)]:
    try:
        html=fetch(url);p=L();p.feed(html);dates=sorted(set(re.findall(r'monetary(20\d{6})a\.htm',html,re.I)));print('FED',label,'count',len(dates),'dates',dates)
    except Exception as e:print('FED_ERR',label,type(e).__name__,str(e))

# BEA form & query
try:
    html=fetch('https://www.bea.gov/news/archive');p=S();p.feed(html);m=[o for o in p.options if o[2].strip()=='Gross Domestic Product'];print('BEA_GDP_OPTIONS',m)
    print('BEA_SELECT_NAMES',sorted(set(o[0] for o in p.options if o[0])))
    if m:
        name,val,_=m[0]
        for y in [2016,2019,2024]:
            q=fetch('https://www.bea.gov/news/archive',{name:val,'field_release_year_value':str(y)});lp=L();lp.feed(q);links=[(h,t) for h,t in lp.links if h and '/news/' in h and ('gross domestic product' in t.lower() or 'gross-domestic-product' in h.lower())];print('BEA',y,'links',len(links),'sample',links[:15])
except Exception as e:print('BEA_ERR',type(e).__name__,str(e))
