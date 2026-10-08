"""Review a ticker + fiscal quarter and export an audited HSBC-style table."""
import argparse
import json
from pathlib import Path

from earnings_core import parse_period,report
from earnings_sources import load_official
from render_earnings import build_html
from render_common import render_files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('symbol');parser.add_argument('--period',default='latest',help='FY2025Q3, 2025第三季, latest; defaults to company fiscal quarter')
    parser.add_argument('-o','--output',required=True,help='output prefix')
    parser.add_argument('--facts',help='verified normalized official facts bundle JSON, instead of automatic fetch')
    parser.add_argument('--cik',type=int,help='verified SEC CIK, when supplied by the user/source')
    parser.add_argument('--analysis',help='source-backed overview/comments JSON; facts are not overwritten')
    parser.add_argument('--no-png',action='store_true');parser.add_argument('--langs',default='zh,en')
    args=parser.parse_args();symbol=args.symbol.strip().upper()
    try:
        period=parse_period(args.period)
        if args.facts:
            bundle=json.loads(Path(args.facts).read_text(encoding='utf-8'))
            if bundle['symbol'].upper()!=symbol:raise ValueError('fact bundle belongs to another symbol')
            if period is None:period=max(bundle['quarters'],key=lambda p:bundle['quarters'][p]['end'])
        else:bundle,period=load_official(symbol,period,args.cik)
        data=report(bundle,period)
        analysis=json.loads(Path(args.analysis).read_text(encoding='utf-8')) if args.analysis else {}
        known={s['id'] for s in data['sources']}
        if analysis and (not analysis.get('source_ids') or any(s not in known for s in analysis['source_ids'])):
            raise ValueError('analyst comments need source_ids from the verified report ledger')
        prefix=Path(args.output);prefix.parent.mkdir(parents=True,exist_ok=True)
        Path(str(prefix)+'_facts.json').write_text(json.dumps(bundle,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        Path(str(prefix)+'_audit.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        languages=[l.strip() for l in args.langs.split(',')]
        if any(l not in ('en','zh') for l in languages):raise ValueError('langs must be zh,en')
        htmls={l:build_html(data,l,analysis) for l in languages}
        for lang,html in htmls.items():Path(str(prefix)+'_'+lang+'.html').write_text(html,encoding='utf-8')
        if not args.no_png:render_files(htmls,str(prefix),scale=3)
        print(f'{symbol} {period}: {data["start"]} to {data["end"]}; '+str(len(data['rows']))+' research rows')
        for warning in data['warnings']:print('source warning:',warning)
    except (ValueError,KeyError,OSError) as exc:parser.exit(2,f'error: {exc}\n')


if __name__=='__main__':main()
