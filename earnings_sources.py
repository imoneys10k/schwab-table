"""Primary quarterly sources: SEC US-GAAP facts; official Apple PDFs; supplied facts.

All cached responses retain original retrieval timestamps. Quarterly values carry
their reported periods and source IDs. No quote-provider financial summaries.
"""
import datetime as dt
import hashlib
import io
import json
import logging
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter,defaultdict
from pathlib import Path

from earnings_core import point,derive,subtract,split_period,previous_period

CACHE=Path(os.environ.get('SCHWAB_EARNINGS_CACHE',Path.home()/'.cache'/'schwab-table'/'earnings'))
TTL=12*3600
UA=os.environ.get('SEC_USER_AGENT','schwab-table quarterly research (+https://github.com/imoneys10k/schwab-table)')


def fetch(url,binary=False):
    CACHE.mkdir(parents=True,exist_ok=True)
    key=hashlib.sha256(url.encode()).hexdigest();data_path=CACHE/(key+('.pdf' if binary else '.json'));meta_path=CACHE/(key+'.meta.json')
    if data_path.exists() and meta_path.exists():
        meta=json.loads(meta_path.read_text())
        if time.time()-meta['saved_at']<TTL:return data_path.read_bytes(),meta
    request=urllib.request.Request(url,headers={'User-Agent':UA,'Accept':'application/pdf' if binary else 'application/json'})
    last=None
    for attempt in range(2):
        try:
            raw=urllib.request.urlopen(request,timeout=25).read()
            meta={'url':url,'retrieved_at':dt.datetime.now(dt.timezone.utc).isoformat(),
                  'saved_at':time.time(),'sha256':hashlib.sha256(raw).hexdigest()}
            data_path.write_bytes(raw);meta_path.write_text(json.dumps(meta,indent=2))
            return raw,meta
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as exc:
            last=exc
            if isinstance(exc,urllib.error.HTTPError) and exc.code in (403,404):break
            if attempt==0:time.sleep(1)
    raise ValueError(f'Official source unavailable: {url} ({last}). Supply a verified official report; no replacement quarter will be invented.')


def _number(text):
    clean=text.strip().replace(',','').replace('$','')
    if clean in ('—','–','-'):return None
    return -float(clean[1:-1]) if clean.startswith('(') and clean.endswith(')') else float(clean)


def _rows(text):
    """Use fixed-layout PDF text; numbers must be whole whitespace-delimited tokens."""
    rows=[]
    for line in text.splitlines():
        parts=re.split(r'\s{2,}',line.strip())
        if len(parts)<2:continue
        label=parts[0].strip();tokens=[]
        for part in parts[1:]:
            tokens.extend(part.replace('$','').split())
        if tokens and all(re.fullmatch(r'\(?-?\d[\d,]*(?:\.\d+)?\)?|[—–-]',t) for t in tokens):
            rows.append((label,[_number(t) for t in tokens]))
    return rows


def _pick(rows,label,occurrence=0):
    def canonical(value):return re.sub(r'\s*\(\d+\)$','',value)
    matches=[values for name,values in rows if canonical(name)==canonical(label)]
    return matches[occurrence] if len(matches)>occurrence else None


def _scaled(value,factor=1e6):
    return None if value is None else value*factor


def _labelled_rows(plain,labels,count):
    """Read known statement rows, tolerating PDF kerning inside words.

    Plain extraction preserves numeric tokens better than layout extraction in
    Apple's older PDFs. A match needs the full expected numeric column count.
    """
    rows=[]
    number=re.compile(r'\s*\$?\s*(\(?-?\d[\d,]*(?:\.\d+)?\)?|[—–-])(?=\s|\$|$)')
    for label in labels:
        base=re.sub(r'\s*\(\d+\)$','',label)
        pattern=r'\s*'.join(re.escape(c) for c in re.sub(r'\s+','',base))+r'\s*(?:\(\d+\))?'
        for match in re.finditer(pattern,plain,re.IGNORECASE):
            pos=match.end();values=[]
            for _ in range(count):
                found=number.match(plain,pos)
                if not found:break
                values.append(_number(found[1]));pos=found.end()
            if len(values)==count:rows.append((label,values))
    return rows


def _dates(text):
    found=re.findall(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d{2})',text)
    return [dt.datetime.strptime(' '.join(t),'%B %d %Y').date().isoformat() for t in found]


def apple_document(year,q):
    from pypdf import PdfReader
    logging.getLogger('pypdf').setLevel(logging.ERROR)
    url=f'https://www.apple.com/newsroom/pdfs/fy{year}-q{q}/FY{year%100:02d}_Q{q}_Consolidated_Financial_Statements.pdf'
    raw,meta=fetch(url,True);reader=PdfReader(io.BytesIO(raw))
    if len(reader.pages)<3:raise ValueError('Apple statement layout changed; inspect the original before importing')
    texts=[p.extract_text(extraction_mode='layout') for p in reader.pages[:3]]
    plain=[p.extract_text() for p in reader.pages[:3]]
    if any(heading not in text for heading,text in zip(('STATEMENTS OF OPERATIONS','BALANCE SHEETS','STATEMENTS OF CASH FLOWS'),plain)):
        raise ValueError('Apple statement order changed; inspect the original before importing')
    if 'Three Months Ended' not in texts[0] or 'In millions' not in texts[0]:
        raise ValueError('Apple PDF does not declare single-quarter income and million-dollar units')
    income_dates=_dates(plain[0])[:2];balance_dates=_dates(plain[1])[:2]
    if len(income_dates)!=2 or len(balance_dates)!=2 or income_dates[0]!=balance_dates[0]:
        raise ValueError('Apple statement dates could not be reconciled')
    source=dict(meta,id=f'apple-FY{year}Q{q}',title=f'Apple FY{year} Q{q} financial statements',kind='company_ir',
        supplemental_pages=max(0,len(reader.pages)-3))
    # Q1 has only current/prior quarter columns; subsequent filings also
    # present cumulative columns. Never consume the next row as extra values.
    income=_labelled_rows(plain[0],list(dict.fromkeys(APPLE_INCOME.values()))+['Diluted'],2 if q==1 else 4)
    balance=_labelled_rows(plain[1],['Cash and cash equivalents','Total assets','Total shareholders’ equity','Commercial paper','Term debt'],2)
    cash=_labelled_rows(plain[2],['Cash generated by operating activities','Payments for acquisition of property, plant and equipment'],2)
    if not _pick(income,'Total net sales (1)') or not _pick(income,'Net income'):
        raise ValueError('Apple statement extraction did not find required reported values')
    return dict(year=year,q=q,income=income,balance=balance,cash=cash,
        ends=income_dates,balance_ends=balance_dates,source=source)


APPLE_INCOME={'revenue':'Total net sales (1)','gross_profit':'Gross margin','operating_income':'Operating income',
    'net_income':'Net income','rd':'Research and development','iphone':'iPhone','mac':'Mac','ipad':'iPad',
    'wearables':'Wearables, Home and Accessories','services':'Services','greater_china':'Greater China'}


def apple_bundle(period):
    if period is None:
        today=dt.date.today();candidates=[f'FY{year}Q{q}' for year in (today.year+1,today.year,today.year-1) for q in (4,3,2,1)]
        candidates=[p for p in candidates if split_period(p)[0]<=today.year or split_period(p)[1]==1]
        # Probe only the most recent company quarters, rather than assuming a
        # calendar quarter has already been disclosed.
        chosen=None
        for candidate in candidates[:6]:
            try:apple_document(*split_period(candidate));chosen=candidate;break
            except ValueError as exc:
                if '404' not in str(exc):raise
        if not chosen:raise ValueError('latest Apple quarter could not be verified')
        period=chosen
    year,q=split_period(period);docs={};sources={};warnings=[]
    def get(y,k,required=False):
        key=f'FY{y}Q{k}'
        if key not in docs:
            try:docs[key]=apple_document(y,k);sources[docs[key]['source']['id']]=docs[key]['source']
            except ValueError as exc:
                if required:raise
                warnings.append(str(exc));docs[key]=None
        return docs[key]
    current=get(year,q,True)
    py,pq=split_period(previous_period(period));previous=get(py,pq,True)
    if pq>1:get(py,pq-1)
    get(year-1,q)
    quarters={};cumulative={}
    # Current-file comparative income is preferred over older as-reported
    # income, while older balance sheets provide actual same-quarter instants.
    for doc in [d for key,d in docs.items() if d and key!=period]+[current]:
        for index,y in enumerate((doc['year'],doc['year']-1)):
            key=f'FY{y}Q{doc["q"]}';end=doc['ends'][index]
            sid=doc['source']['id']
            # Cumulative cash flow does not require the single-quarter start.
            # Retain it even when this older quarter's preceding date is absent.
            for metric,label in [('cfo','Cash generated by operating activities'),('capex','Payments for acquisition of property, plant and equipment')]:
                values=_pick(doc['cash'],label)
                if values and len(values)==2:
                    amount=_scaled(values[index],1e6*(-1 if metric=='capex' else 1))
                    cumulative[(key,metric)]=point(amount,'USD',None,end,[sid],method='reported cumulative cash flow',
                        fiscal_year=y,fiscal_quarter=doc['q'],page=3,reported_value=values[index],reported_unit='USD million')
            prior_doc=docs.get(previous_period(key))
            if prior_doc:start=(dt.date.fromisoformat(prior_doc['ends'][0])+dt.timedelta(days=1)).isoformat()
            elif doc['q']==1:
                # The balance-sheet comparative date is the prior fiscal year
                # end only for the current fiscal year, not the prior-year YTD.
                if index==0:start=(dt.date.fromisoformat(doc['balance_ends'][1])+dt.timedelta(days=1)).isoformat()
                else:continue
            else:
                matching=next((d for d in docs.values() if d and d['q']==doc['q']-1 and d['year']==y+1),None)
                if not matching:continue
                start=(dt.date.fromisoformat(matching['ends'][1])+dt.timedelta(days=1)).isoformat()
            quarter=quarters.setdefault(key,{'start':start,'end':end,'metrics':{}})
            if quarter['end']!=end:raise ValueError('inconsistent comparative quarter dates')
            for metric,label in APPLE_INCOME.items():
                values=_pick(doc['income'],label)
                if values and len(values)==(2 if doc['q']==1 else 4):
                    quarter['metrics'][metric]=point(_scaled(values[index]),'USD',start,end,[sid],reported_label=label,page=1)
            eps=_pick(doc['income'],'Diluted')
            if eps and len(eps)==(2 if doc['q']==1 else 4):quarter['metrics']['eps']=point(eps[index],'USD/shares',start,end,[sid],reported_label='Diluted EPS',page=1)
            if index==0:
                for metric,label in [('cash','Cash and cash equivalents'),('assets','Total assets'),('equity','Total shareholders’ equity')]:
                    values=_pick(doc['balance'],label)
                    if values and len(values)==2:quarter['metrics'][metric]=point(_scaled(values[0]),'USD',None,end,[sid],page=2,reported_label=label)
                paper=_pick(doc['balance'],'Commercial paper');terms=[v for name,v in doc['balance'] if name=='Term debt']
                if paper and len(terms)==2 and all(v is not None for v in (paper[0],terms[0][0],terms[1][0])):
                    quarter['metrics']['debt']=point((paper[0]+terms[0][0]+terms[1][0])*1e6,'USD',None,end,[sid],
                        method='sum of commercial paper and current/non-current term debt',page=2)
    for key,quarter in quarters.items():
        _,cq=split_period(key)
        for metric in ('cfo','capex'):
            now=cumulative.get((key,metric))
            if cq==1 and now:
                quarter['metrics'][metric]=dict(now,start=quarter['start'],method='reported',cashflow_scope='first quarter')
            elif now:
                derived=subtract(now,cumulative.get((previous_period(key),metric)),quarter['start'],quarter['end'])
                if derived:quarter['metrics'][metric]=derived
        derive(quarter)
    if period not in quarters:raise ValueError('Apple target quarter could not be reconciled')
    return dict(symbol='AAPL',company_name='Apple Inc.',currency='USD',quarters=quarters,
        sources=list(sources.values()),warnings=warnings),period


SEC_TAGS={
 'revenue':('RevenueFromContractWithCustomerExcludingAssessedTax','Revenues','SalesRevenueNet'),
 'gross_profit':('GrossProfit',),'operating_income':('OperatingIncomeLoss',),'net_income':('NetIncomeLoss',),
 'eps':('EarningsPerShareDiluted',),'cfo':('NetCashProvidedByUsedInOperatingActivities',),
 'capex':('PaymentsToAcquirePropertyPlantAndEquipment',),'rd':('ResearchAndDevelopmentExpense',),
 'cash':('CashAndCashEquivalentsAtCarryingValue',),'assets':('Assets',),'equity':('StockholdersEquity',)}
INSTANT={'cash','assets','equity'}


def sec_bundle(symbol,period,cik=None):
    if cik is None:
        raw,_=fetch('https://www.sec.gov/files/company_tickers.json');tickers=json.loads(raw)
        matches=[v for v in tickers.values() if v['ticker'].upper()==symbol]
        if not matches:raise ValueError(f'{symbol}: no verified SEC ticker mapping; use an official supplied report')
        cik=matches[0]['cik_str']
    cik=int(cik);url=f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json';raw,meta=fetch(url);data=json.loads(raw)
    if int(data.get('cik',-1))!=cik:raise ValueError('SEC entity CIK does not match ticker mapping')
    taxonomy=data.get('facts',{}).get('us-gaap',{})
    if not taxonomy:raise ValueError('automatic provider currently requires US-GAAP 10-Q/10-K facts; import the issuer report')
    records=[]
    for metric,tags in SEC_TAGS.items():
        for tag in tags:
            for unit,values in taxonomy.get(tag,{}).get('units',{}).items():
                for value in values:
                    if value.get('form') not in ('10-Q','10-Q/A','10-K','10-K/A'):continue
                    if value.get('fy') and value.get('fp') in ('Q1','Q2','Q3','FY'):
                        records.append(dict(value,metric=metric,tag=tag,unit=unit))
    by_acc=defaultdict(list)
    for r in records:by_acc[r['accn']].append(r)
    anchors={}
    for acc,items in by_acc.items():
        fy,fp=Counter((r['fy'],r['fp']) for r in items).most_common(1)[0][0]
        key=f'FY{fy}Q{4 if fp=="FY" else fp[1]}'
        primary=[r for r in items if r['metric']=='assets' and not r.get('start')]
        if not primary:primary=[r for r in items if r['metric']=='revenue' and r.get('start')]
        if not primary:primary=items
        end=max(r['end'] for r in primary)
        anchor=dict(acc=acc,end=end,year=fy,fp=fp,filed=max(r['filed'] for r in items))
        if key not in anchors or (anchor['end'],anchor['filed'])>(anchors[key]['end'],anchors[key]['filed']):anchors[key]=anchor
    if not anchors:raise ValueError('no quarterly/annual US-GAAP filing anchors found')
    if period is None:period=max(anchors,key=lambda k:(anchors[k]['end'],anchors[k]['filed']))
    if period not in anchors:raise ValueError(f'{period}: corresponding SEC filing not found; another quarter will not be substituted')
    y,q=split_period(period);wanted={period,previous_period(period),f'FY{y-1}Q{q}'}
    for key in list(wanted):
        if split_period(key)[1]>1:wanted.add(previous_period(key))
    target=anchors[period]
    reporting_units={r['unit'] for r in by_acc[target['acc']] if r['metric']=='revenue' and r['end']==target['end']}
    if 'USD' in reporting_units:currency='USD'
    elif len(reporting_units)==1:currency=next(iter(reporting_units))
    else:raise ValueError('SEC reporting currency is ambiguous; use a verified normalized issuer report')
    sources=[];quarters={};cumulative={}
    for key in sorted(wanted):
        if key not in anchors:continue
        a=anchors[key];fy,cq=split_period(key);items=by_acc[a['acc']]
        income=[r for r in items if r['metric']=='revenue' and r.get('start') and r['end']==a['end']]
        direct=[r for r in income if 60<=(dt.date.fromisoformat(r['end'])-dt.date.fromisoformat(r['start'])).days+1<=110]
        previous=anchors.get(previous_period(key))
        if direct:start=max(direct,key=lambda r:r['filed'])['start']
        elif previous:start=(dt.date.fromisoformat(previous['end'])+dt.timedelta(days=1)).isoformat()
        else:continue
        sid='sec-'+a['acc'];sources.append(dict(meta,id=sid,title=f'{data.get("entityName",symbol)} {key} filing',
            published_at=a['filed'],url=f'https://www.sec.gov/Archives/edgar/data/{cik}/{a["acc"].replace("-","")}/{a["acc"]}-index.html',kind='regulator'))
        quarter={'start':start,'end':a['end'],'metrics':{}}
        for metric,tags in SEC_TAGS.items():
            unit=currency+'/shares' if metric=='eps' else currency
            found=None
            for tag in tags:
                candidates=[r for r in items if r['tag']==tag and r['unit']==unit and r['end']==a['end']]
                if metric!='eps' and metric not in INSTANT:
                    long=[r for r in candidates if r.get('start') and 60<=(dt.date.fromisoformat(r['end'])-dt.date.fromisoformat(r['start'])).days+1<=400]
                    if long:
                        c=max(long,key=lambda r:(dt.date.fromisoformat(r['end'])-dt.date.fromisoformat(r['start'])).days)
                        cumulative[(key,metric)]=point(c['val'],unit,c['start'],c['end'],[sid],fiscal_year=fy,tag=tag)
                selected=[r for r in candidates if r.get('start')==start] if metric not in INSTANT else [r for r in candidates if not r.get('start')]
                if selected:found=max(selected,key=lambda r:r['filed']);break
            if found:quarter['metrics'][metric]=point(found['val'],unit,found.get('start'),found['end'],[sid],tag=found['tag'])
        quarters[key]=quarter
    # Prefer the same filing's restated/split-adjusted prior-year comparative
    # facts when their actual quarter/YTD dates match an established anchor.
    for key,quarter in quarters.items():
        fy,cq=split_period(key);comparison=f'FY{fy+1}Q{cq}'
        if fy+1>y or comparison not in anchors:continue
        acc=anchors[comparison]['acc'];sid='sec-'+acc
        if not any(s['id']==sid for s in sources):continue
        for metric,tags in SEC_TAGS.items():
            if metric in INSTANT:continue
            unit=currency+'/shares' if metric=='eps' else currency
            matches=[r for r in by_acc[acc] if r['metric']==metric and r['unit']==unit and r['end']==quarter['end']]
            direct=[r for r in matches if r.get('start')==quarter['start']]
            if direct:
                r=max(direct,key=lambda r:r['filed'])
                quarter['metrics'][metric]=point(r['val'],unit,r['start'],r['end'],[sid],tag=r['tag'],method='current filing comparative')
            cumulative_old=cumulative.get((key,metric))
            if metric!='eps' and cumulative_old:
                candidates=[r for r in matches if r.get('start')==cumulative_old['start']]
                if candidates:
                    r=max(candidates,key=lambda r:r['filed'])
                    cumulative[(key,metric)]=point(r['val'],unit,r['start'],r['end'],[sid],fiscal_year=fy,tag=r['tag'],method='current filing YTD comparative')
    for key,quarter in quarters.items():
        cq=split_period(key)[1]
        for metric in SEC_TAGS:
            if metric in INSTANT or metric=='eps' or metric in quarter['metrics']:continue
            current=cumulative.get((key,metric))
            if cq==1 and current and current['start']==quarter['start']:quarter['metrics'][metric]=current
            elif cq>1:
                value=subtract(current,cumulative.get((previous_period(key),metric)),quarter['start'],quarter['end'])
                if value:quarter['metrics'][metric]=value
        derive(quarter)
    return dict(symbol=symbol,company_name=data.get('entityName',symbol),currency=currency,quarters=quarters,
        sources=sources,warnings=['Q4 flow facts may be derived from FY minus nine months. Diluted EPS is never derived by subtracting annual EPS.']),period


def load_official(symbol,period,cik=None):
    if symbol=='AAPL':
        # Direct issuer statements disclose single-quarter EPS and segments, and
        # remain available when the SEC data endpoint declines automated access.
        return apple_bundle(period)
    return sec_bundle(symbol,period,cik)
