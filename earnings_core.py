"""Quarterly financial facts, audited arithmetic and report comparisons."""
import datetime as dt
import math
import re
import copy

# key, Chinese, English, section, unit type, direction interpretation
METRICS=[
('revenue','營收','Revenue','income','money','higher'),
('gross_profit','毛利','Gross profit','income','money','higher'),
('gross_margin','毛利率','Gross margin','income','pct','higher'),
('operating_income','營業利益','Operating income','income','money','higher'),
('operating_margin','營業利潤率','Operating margin','income','pct','higher'),
('net_income','淨利潤','Net income','income','money','higher'),
('net_margin','淨利率','Net margin','income','pct','higher'),
('eps','稀釋每股收益','Diluted EPS','income','eps','higher'),
('cfo','營運現金流','Operating cash flow','cashflow','money','higher'),
('capex','購置固定資產支出','Capital expenditure','cashflow','money','observe'),
('fcf','自由現金流','Free cash flow','cashflow','money','higher'),
('rd','研發費用','Research and development','cashflow','money','observe'),
('cash','現金及約當現金','Cash and equivalents','balance','money','observe'),
('debt','有息債務','Interest-bearing debt','balance','money','observe'),
('assets','總資產','Total assets','balance','money','observe'),
('equity','股東權益','Shareholders equity','balance','money','observe'),
('iphone','iPhone 營收','iPhone revenue','business','money','higher'),
('mac','Mac 營收','Mac revenue','business','money','higher'),
('ipad','iPad 營收','iPad revenue','business','money','higher'),
('wearables','穿戴／家用／配件營收','Wearables, home and accessories','business','money','higher'),
('services','服務營收','Services revenue','business','money','higher'),
('greater_china','大中華區營收','Greater China revenue','business','money','higher')]


def parse_period(text):
    value=re.sub(r'\s+','',str(text)).upper()
    if value in ('LATEST','最新','最近一季','最新一季'):return None
    if value.startswith('CY') or '自然' in value or '日曆' in value or '日历' in value:
        raise ValueError('Calendar quarters need verified company-period mapping. Supply the matching fiscal quarter or an official normalized report.')
    match=re.search(r'(?:FY)?(20\d{2})(?:年|財年|财年)?Q([1-4])',value)
    if not match:match=re.search(r'Q([1-4])(?:FY)?(20\d{2})',value)
    if match:
        parts=match.groups();year,quarter=(int(parts[1]),int(parts[0])) if len(parts[0])==1 else (int(parts[0]),int(parts[1]))
    else:
        match=re.search(r'(20\d{2})(?:年|財年|财年)?第?([一二三四1234])(?:季度|季)',value)
        if not match:raise ValueError('period must include fiscal year and quarter, e.g. FY2025Q3, 2025第三季, or latest')
        year=int(match[1]);quarter=int(match[2]) if match[2].isdigit() else '一二三四'.index(match[2])+1
    return f'FY{year}Q{quarter}'


def split_period(period):
    match=re.fullmatch(r'FY(20\d{2})Q([1-4])',period)
    if not match:raise ValueError('invalid fiscal period')
    return int(match[1]),int(match[2])


def previous_period(period):
    year,q=split_period(period)
    return f'FY{year}Q{q-1}' if q>1 else f'FY{year-1}Q4'


def point(value,unit,start,end,source_ids,method='reported',**extra):
    if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)):
        raise ValueError('financial values must be finite numbers or null')
    return dict(value=value,unit=unit,start=start,end=end,source_ids=list(dict.fromkeys(source_ids)),method=method,**extra)


def subtract(current,previous,start,end):
    if not current or not previous:return None
    if current['unit']!=previous['unit']:return None
    if current['value'] is None or previous['value'] is None:return None
    if current.get('fiscal_year') is None or current.get('fiscal_year')!=previous.get('fiscal_year'):return None
    if current.get('start') and previous.get('start') and current['start']!=previous['start']:return None
    if current['end']!=end or (dt.date.fromisoformat(previous['end'])+dt.timedelta(days=1)).isoformat()!=start:return None
    return point(current['value']-previous['value'],current['unit'],start,end,
        current['source_ids']+previous['source_ids'],'YTD difference',components=[current,previous])


def derive(quarter):
    metrics=quarter['metrics'];start,end=quarter['start'],quarter['end']
    for key,numerator in [('gross_margin','gross_profit'),('operating_margin','operating_income'),('net_margin','net_income')]:
        top,base=metrics.get(numerator),metrics.get('revenue')
        if key not in metrics and top and base and top['value'] is not None and base['value'] is not None and base['value']>0 and top['unit']==base['unit']:
            metrics[key]=point(top['value']/base['value']*100,'%',start,end,top['source_ids']+base['source_ids'],
                'ratio',components=[top,base])
    cfo,capex=metrics.get('cfo'),metrics.get('capex')
    if 'fcf' not in metrics and cfo and capex and cfo['value'] is not None and capex['value'] is not None and cfo['unit']==capex['unit']:
        metrics['fcf']=point(cfo['value']-capex['value'],cfo['unit'],start,end,
            cfo['source_ids']+capex['source_ids'],'CFO minus PPE expenditure',components=[cfo,capex])
    return quarter


def validate(bundle):
    sources={s['id']:s for s in bundle.get('sources',[])}
    if not sources:raise ValueError('report needs an inspectable source ledger')
    for source in sources.values():
        if not source.get('url') or not source.get('retrieved_at'):
            raise ValueError('each source needs URL/path and retrieval time')
    kinds={m[0]:m[4] for m in METRICS}
    for key,quarter in bundle['quarters'].items():
        split_period(key)
        start,end=dt.date.fromisoformat(quarter['start']),dt.date.fromisoformat(quarter['end'])
        if not 60<=(end-start).days+1<=110:
            raise ValueError(f'{key}: a single quarter cannot be an annual / YTD period')
        for name,fact in quarter['metrics'].items():
            if fact is None:continue
            value=fact['value']
            if value is not None and (isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value)):
                raise ValueError(f'{key}.{name}: nonfinite or nonnumeric value')
            if fact['end']!=quarter['end']:
                raise ValueError(f'{key}.{name}: end date differs from requested quarter')
            if fact.get('start') and fact['start']!=quarter['start']:
                raise ValueError(f'{key}.{name}: cumulative data has not been converted to a quarter')
            if name in kinds and name not in ('cash','debt','assets','equity') and fact.get('start')!=quarter['start']:
                raise ValueError(f'{key}.{name}: flow facts need the verified single-quarter start date')
            kind=kinds.get(name)
            expected='%' if kind=='pct' else bundle['currency']+'/shares' if kind=='eps' else bundle['currency']
            if kind and fact.get('unit')!=expected:
                raise ValueError(f'{key}.{name}: incompatible reporting currency/unit')
            if not fact.get('source_ids') or any(s not in sources for s in fact['source_ids']):
                raise ValueError(f'{key}.{name}: missing source evidence')
    return bundle


def change(now,before,kind):
    if not now or not before or now['value'] is None or before['value'] is None:return None
    if now['unit']!=before['unit']:return None
    a,b=now['value'],before['value']
    if kind=='pct':return dict(value=a-b,unit='pp',delta=a-b)
    if b<=0:return dict(value=None,unit='%',delta=a-b,reason='non-positive comparison base')
    return dict(value=(a/b-1)*100,unit='%',delta=a-b)


def report(bundle,period):
    bundle=copy.deepcopy(bundle)
    for quarter in bundle['quarters'].values():derive(quarter)
    validate(bundle)
    if period not in bundle['quarters']:raise ValueError(f'{period}: no corresponding official quarterly statement; another period will not be substituted')
    current=bundle['quarters'][period];year,q=split_period(period)
    yoy=bundle['quarters'].get(f'FY{year-1}Q{q}',{}).get('metrics',{})
    qoq=bundle['quarters'].get(previous_period(period),{}).get('metrics',{})
    rows=[]
    for key,zh,en,group,kind,direction in METRICS:
        if group=='business' and key not in current['metrics']:continue
        value=current['metrics'].get(key);prior=yoy.get(key);previous=qoq.get(key)
        year_change=change(value,prior,kind);quarter_change=change(value,previous,kind)
        if not value or value['value'] is None or year_change is None:view='unassessed'
        elif direction=='observe' or year_change['delta']==0:view='neutral'
        else:view='up' if year_change['delta']>0 else 'down'
        rows.append(dict(key=key,label={'zh':zh,'en':en},group=group,format=kind,
            fact=value,yoy=year_change,qoq=quarter_change,view=view,
            comparison_sources=list(dict.fromkeys((prior or {}).get('source_ids',[])+(previous or {}).get('source_ids',[])))))
    return dict(symbol=bundle['symbol'],company_name=bundle.get('company_name',bundle['symbol']),
        period=period,start=current['start'],end=current['end'],currency=bundle['currency'],
        rows=rows,sources=bundle['sources'],warnings=bundle.get('warnings',[]),
        interpretation='Operating indicators reflect observed YoY direction; spending and balance-sheet changes require context. No buy/sell or consensus surprise classification.')
