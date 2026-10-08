"""Prepare Morgan/Blackstone report specs from fetch_prices.py daily closes.

Fiscal/company forecasts and portfolio exposure are never inferred from prices.
Morgan: YTD and trailing-year return / volatility / drawdown. Blackstone: two
return periods. Uses the established chart calculations and actual source dates.
"""
import argparse
import calendar
import datetime as dt
import json
import math
from html import escape
from pathlib import Path

from render_chart import Series


def previous_year(date):
    year = date.year - 1
    return dt.date(year, date.month, min(date.day, calendar.monthrange(year, date.month)[1]))


def prepare(data, style, names=None, include_benchmarks=False):
    if style not in ('morgan', 'blackstone'):
        raise ValueError('prices_to_table supports morgan and blackstone; IBKR needs actual holdings')
    if data.get('errors'):
        raise ValueError('price input contains fetch errors; resolve them before preparing a report')
    raw = {k:v for k,v in data['series'].items() if include_benchmarks or not v.get('benchmark')}
    if not raw:
        raise ValueError('no selected price series')
    for symbol, entry in raw.items():
        seen=set()
        for date,close in entry['points']:
            dt.date.fromisoformat(date)
            if date in seen or not isinstance(close,(int,float)) or isinstance(close,bool) or not math.isfinite(close) or close<=0:
                raise ValueError(f'{symbol}: closes must be positive, finite and unique by date')
            seen.add(date)
    common = set.intersection(*[{p[0] for p in v['points']} for v in raw.values()])
    common = {day for day in common if day <= data['end']}
    if not common:
        raise ValueError('selected listings have no shared closing date')
    end = dt.date.fromisoformat(max(common))
    periods = [('ytd', dt.date(end.year-1, 12, 31)), ('year', previous_year(end))]
    bases = {k:{} for k,_ in periods};rows = []
    basis = {v.get('basis', 'price') for v in raw.values()}
    if len(basis) != 1:
        raise ValueError('price returns and total returns cannot be mixed')
    for symbol, entry in raw.items():
        info = (names or {}).get(symbol, {})
        row = {'ticker':symbol,'name':info.get('name', {'en':symbol,'zh':symbol}),
            'group':info.get('group', {'en':'Listed Securities','zh':'上市證券'}),
            'level':2,'bench':bool(entry.get('benchmark')),'values':{}}
        for key, start in periods:
            series = Series(symbol, entry['points'], start, end)
            if series.dates[-1] != end:
                raise ValueError(f'{symbol}: cannot reach common close {end}')
            row['values'][key+'_return'] = series.ret
            daily = all((b-a).days<=14 for a,b in zip(series.dates,series.dates[1:]))
            row['values'][key+'_vol'] = series.vol if len(series.dates) >= 3 and daily else None
            row['values'][key+'_drawdown'] = series.mdd if daily else None
            bases[key][symbol] = {'date':series.base_date.isoformat(),'close':series.close[0],
                'end_close':series.close[-1],'observations':len(series.close)}
        rows.append(row)
    columns = [{'key':'name','label':{'en':'','zh':''},'format':'text',
                'width':29.44 if style=='morgan' else 52}]
    if style == 'morgan':
        for key,_ in periods:
            for suffix,en,zh in [('return','Return\n(%)','回報\n(%)'),('vol','Annualized\nvolatility (%)','年化\n波動率 (%)'),('drawdown','Max drawdown\n(%)','最大回撤\n(%)')]:
                columns.append({'key':key+'_'+suffix,'label':{'en':en,'zh':zh},'format':'pct','width':11.76})
    else:
        for key,en,zh in [('ytd','YTD','年初至今'),('year','Trailing 1Y','近一年')]:
            columns.append({'key':key+'_return','label':{'en':en,'zh':zh},'format':'pct','width':24})
    sources = '; '.join(dict.fromkeys(v.get('source','Not supplied') for v in raw.values()))
    retrieved = '; '.join(f'{k}: {v.get("fetched_at", "not supplied")}' for k,v in raw.items())
    warnings = '; '.join(str(w) for w in data.get('warnings', []))
    basis_text = 'Total returns from user-supplied adjusted closes.' if basis == {'total'} else 'Price returns, excluding dividends; each listing in its own currency, without FX conversion.'
    unadjusted = any('unadjusted' in v.get('source','').lower() for v in raw.values())
    detail = ' Unadjusted exchange closes can be affected by corporate actions.' if unadjusted else ''
    if include_benchmarks and any(v.get('benchmark') and v.get('class')=='etf' for v in raw.values()):
        detail += ' Benchmark ETFs are index proxies, not the indexes themselves.'
    en_foot = f'Source: {escape(sources)}. Common close: {end}. Retrieved: {escape(retrieved)}. {basis_text}{detail} YTD starts at the last close of the prior year; trailing year starts at the last close on or before {previous_year(end)}. Volatility is sample daily-return standard deviation × √252; drawdown is the largest observed decline from the running peak. Insufficient daily history is NA for risk metrics. '
    zh_foot = f'資料來源：{escape(sources)}。共同收盤日：{end}；資料取得時間：{escape(retrieved)}。'+ ('回報由使用者提供的調整收盤價計算，包含股息再投資。' if basis=={'total'} else '價格回報不含股息，各上市幣別分別計算，未作匯率換算。')
    if unadjusted:zh_foot += '交易所未復權收盤價可能受到除權事件影響。'
    zh_foot += f'年初至今以上一年最後收盤價為起點；近一年以{previous_year(end)}或之前最近收盤價為起點。年化波動率為日回報樣本標準差×√252；最大回撤為所提供日線中自前高的最大跌幅，日線不足時風險指標填NA。'
    if warnings:
        en_foot += 'Data warnings: '+escape(warnings)+'. ';zh_foot += '資料警告：'+escape(warnings)+'。'
    en_foot += '<b>Past performance is no guarantee of future results.</b>'
    zh_foot += '<b>過往業績不代表未來表現。</b>'
    spec = {'style':style,'as_of':end.isoformat(),'columns':columns,'rows':rows,
        'calculation':{'end':end.isoformat(),'bases':bases,'return_basis':next(iter(basis))},
        'langs':{'en':{'title':'Equity Performance','subtitle':('Total returns / dividends reinvested' if basis=={'total'} else 'Price appreciation / excluding dividends'),'foot':en_foot},
                 'zh':{'title':'股票表現','subtitle':('總回報／股息再投資' if basis=={'total'} else '價格變動／不含股息'),'foot':zh_foot}}}
    if style == 'morgan':
        spec['column_groups']=[{'label':{'en':f'YTD\nAS OF {end}','zh':f'年初至今\n截至 {end}'},'keys':[c['key'] for c in columns[1:4]]},
            {'label':{'en':f'TRAILING YEAR\nAS OF {end}','zh':f'近一年\n截至 {end}'},'keys':[c['key'] for c in columns[4:]]}]
        for L in spec['langs'].values():L.pop('subtitle')
    return spec


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data');parser.add_argument('output')
    parser.add_argument('--style',choices=['morgan','blackstone'],required=True)
    parser.add_argument('--names',help='JSON map: symbol -> {name:{en,zh},group:{en,zh}}')
    parser.add_argument('--include-benchmarks',action='store_true')
    args=parser.parse_args()
    try:
        data=json.loads(Path(args.data).read_text(encoding='utf-8'))
        names=json.loads(Path(args.names).read_text(encoding='utf-8')) if args.names else None
        spec=prepare(data,args.style,names,args.include_benchmarks)
    except (ValueError,KeyError,OSError) as exc:
        parser.exit(2,f'error: {exc}\n')
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'wrote {output}; common close {spec["as_of"]}')


if __name__=='__main__':main()
