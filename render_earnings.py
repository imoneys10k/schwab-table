"""HSBC-inspired quarterly research table, with factual values and source links."""
from html import escape
from fonts import font_face_css
from localization import traditional_html

GROUPS={'income':{'en':'REVENUE AND PROFITABILITY','zh':'營收與盈利'},
 'cashflow':{'en':'CASH FLOW AND INVESTMENT','zh':'現金流與資本投入'},
 'balance':{'en':'FINANCIAL POSITION','zh':'財務結構'},
 'business':{'en':'BUSINESS AND MARKET DRIVERS','zh':'業務與市場驅動'}}


def number(fact,kind):
    if not fact or fact['value'] is None:return 'NA'
    value=fact['value']
    if kind=='money':return f'{value/1e6:,.1f}'
    if kind=='eps':return f'{value:.2f}'
    return f'{value:.2f}%'


def delta(value,lang):
    if value is None:return 'NA'
    if value['value'] is None:return '基期非正，不計百分比' if lang=='zh' else 'non-positive base; no percentage'
    return f'{value["value"]:+.2f}'+ (' 個百分點' if lang=='zh' and value['unit']=='pp' else ' pp' if value['unit']=='pp' else '%')


def marker(view):
    if view=='unassessed':return '<span class="missing" aria-label="Insufficient comparison evidence">—</span>'
    shapes={'up':('2,7 5,1 8,7','#008580'),'down':('2,1 8,1 5,7','#a8000b'),
            'neutral':('2,1 8,4 2,7','#e8a215')}
    points,color=shapes[view]
    return f'<svg width="10" height="8" viewBox="0 0 10 8" role="img" aria-label="{view}"><polygon points="{points}" fill="{color}"/></svg>'


def commentary(row,lang,analysis):
    fact=row['fact'];prefix='本季' if lang=='zh' else 'Quarter'
    if fact and fact.get('start') is None:prefix='季末' if lang=='zh' else 'Quarter end'
    text=f'{prefix}: {number(fact,row["format"])}; '+ ('同比: ' if lang=='zh' else 'YoY: ')+delta(row['yoy'],lang)+'; '+('環比: ' if lang=='zh' else 'QoQ: ')+delta(row['qoq'],lang)+'.'
    if not fact or fact['value'] is None:
        text += ' 未取得對應單季資料。' if lang=='zh' else ' Corresponding single-quarter fact not obtained.'
    elif not fact['method'].startswith('reported') and fact['method'] not in ('current filing comparative','ratio'):
        text += ' 由已披露累計值／組成項推導，詳見來源台帳。' if lang=='zh' else ' Derived from disclosed cumulative/component facts; see audit ledger.'
    if row['key']=='capex':
        text += ' 支出增減本身不判定好壞。' if lang=='zh' else ' Higher/lower spending alone is not graded as good/bad.'
    overrides=analysis.get('comments',{}).get(row['key'],{})
    if overrides:
        text += ' '+overrides.get(lang,overrides.get('en',''))
    return text


def build_html(report,lang='zh',analysis=None):
    analysis=analysis or {};rows=[];group=None
    for row in report['rows']:
        if row['group']!=group:
            group=row['group'];rows.append(f'<tr class="group"><th colspan="3">{GROUPS[group][lang]}</th></tr>')
        sources=list(dict.fromkeys((row['fact'] or {}).get('source_ids',[])+row.get('comparison_sources',[])))
        refs=' '.join(f'[{i+1}]' for i,s in enumerate(report['sources']) if s['id'] in sources)
        rows.append(f'<tr data-metric="{row["key"]}" data-view="{row["view"]}"><td>{escape(row["label"][lang])}</td><td class="view">{marker(row["view"])}</td><td>{escape(commentary(row,lang,analysis))} <span class="refs">{refs}</span></td></tr>')
    title=f'{report["company_name"]} ({report["symbol"]}) · {report["period"]}'
    subtitle=('季度財報與市場研究' if lang=='zh' else 'Quarterly Financial and Market Review')
    period=('公司財季' if lang=='zh' else 'Company fiscal quarter')+f': {report["start"]} — {report["end"]}'
    labels=['財務項目','同比','本季結果與研究評論'] if lang=='zh' else ['Financial item','YoY','Quarter results and research comment']
    legend='▲ 核心經營指標同比增加　▼ 同比減少　▶ 中性／需解讀　— 比較資料不足' if lang=='zh' else '▲ Higher core operating indicator YoY · ▼ Lower YoY · ▶ Context required · — Insufficient evidence'
    foot=('金額為百萬 '+report['currency']+'；每股收益為 '+report['currency']+'/股；利潤率同比與環比用百分點。營運現金流按單季呈現，累計值須先拆季；自由現金流＝營運現金流−購置固定資產支出。三角反映同比方向，並非投資評級；環比受季節性影響。未取得發布前一致預期時，不判定超／低於預期。' if lang=='zh' else
          'Amounts in '+report['currency']+' millions; EPS in '+report['currency']+'/share. Margin changes in percentage points. Cash flow is single-quarter, derived from cumulative disclosures when necessary; FCF = CFO minus PPE expenditure. Triangles show YoY direction, not investment ratings; QoQ is seasonal. No beat/miss classification without pre-release consensus evidence.')
    links=[]
    for i,source in enumerate(report['sources']):
        links.append(f'<div>[{i+1}] <a href="{escape(source["url"],quote=True)}">{escape(source.get("title",source["id"]))}</a> · '+('取得：' if lang=='zh' else 'Retrieved: ')+escape(source['retrieved_at'])+'</div>')
    fcf=next((row['fact'] for row in report['rows'] if row['key']=='fcf'),None)
    if fcf and fcf.get('method')!='CFO minus PPE expenditure':
        foot=foot.replace('自由現金流＝營運現金流−購置固定資產支出。','自由現金流按已核實披露口徑，定義詳來源。').replace('FCF = CFO minus PPE expenditure.','FCF follows the verified disclosed definition; see sources.')
    overview=analysis.get('overview',{}).get(lang,'')
    overview_html='<p class="overview">'+escape(overview)+'</p>' if overview else ''
    html=f'''<!doctype html><html lang="{'zh-Hant' if lang=='zh' else 'en'}"><head><meta charset="utf-8"><title>{escape(title)}</title><style>
{font_face_css('ibkr')}
*{{box-sizing:border-box}}body{{margin:0;background:#fff;font-family:Arial,"Droid Sans","Noto Sans CJK TC","PingFang TC","Microsoft JhengHei",sans-serif;color:#555}}#wrap{{width:625px;padding:18px;background:white}}h1{{font-size:14.04px;font-weight:400;color:#000;margin:0 0 3px}}h2{{font-size:12px;color:#000;margin:0 0 5px}}.period{{font-size:8px;margin:0 0 6px;color:#555}}table{{width:100%;border-collapse:collapse;table-layout:fixed;font-size:8.04px;line-height:1.2}}th{{font-weight:400;color:#000;text-align:left;padding:2px 4px;border-top:1px solid #000;border-bottom:1px solid #666}}td{{padding:3px 4px;border-bottom:.45px solid #b0b0b0;vertical-align:middle;overflow-wrap:anywhere}}.view{{text-align:center}}.group th{{background:#d7d8d6;font-weight:600;padding:2px 4px;border-top:.45px solid #b0b0b0;border-bottom:.45px solid #b0b0b0}}.legend{{font-size:7px;margin:7px 0;color:#555}}.foot,.sources{{font-size:6.5px;line-height:1.35;margin-top:6px}}.refs{{font-size:6px;color:#777;white-space:nowrap}}a{{color:#555;text-decoration:none}}.overview{{font-size:9px;line-height:1.4;margin:0 0 8px}}.missing{{color:#888}}
</style></head><body><div id="wrap"><h1>{escape(title)}</h1><h2>{subtitle}</h2><p class="period">{period}<br>{'單位：' if lang=='zh' else 'Units: '}{report['currency']} {'百萬；EPS為' if lang=='zh' else 'million; EPS in '}{report['currency']}/{'股' if lang=='zh' else 'share'}</p>{overview_html}<table><colgroup><col style="width:16%"><col style="width:5%"><col style="width:79%"></colgroup><thead><tr>{''.join('<th>'+l+'</th>' for l in labels)}</tr></thead><tbody>{''.join(rows)}</tbody></table><p class="legend">{legend}</p><div class="foot">{foot}</div><div class="sources">{''.join(links)}</div></div></body></html>'''
    return traditional_html(html) if lang=='zh' else html
