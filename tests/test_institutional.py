import copy
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from render_table import build_html
from localization import traditional_html
from prices_to_table import prepare


class Cells(HTMLParser):
    def __init__(self, html):
        super().__init__(); self.values = []; self.symbols = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'td' and 'data-key' in attrs:
            self.values.append((attrs['data-key'], json.loads(attrs['data-value'])))
        if tag == 'tr' and 'data-symbol' in attrs:
            self.symbols.append(attrs['data-symbol'])


def spec(style):
    cols = [{'key':'name','label':{'en':'Name','zh':'证券名称'}}]
    keys = ['r1','v1','d1','r2','v2','d2'] if style == 'morgan' else ['return','value']
    cols += [{'key':key,'label':key,'format':'pct'} for key in keys]
    value = {'style':style,'langs':{l:{'title':'投资表现' if l=='zh' else 'Performance','foot':'来源'} for l in ('en','zh')},
        'columns':cols,'rows':[
            {'ticker':'LOW','name':{'en':'Low <script> & Co','zh':'低收益证券'},'group':'Group A','values':dict.fromkeys(keys,-8.7)},
            {'ticker':'HIGH','name':{'en':'High','zh':'高收益证券'},'group':'Group B','values':dict.fromkeys(keys,31.2)},
            {'ticker':'MISS','name':{'en':'Missing','zh':'缺失'},'group':'Group B','values':dict.fromkeys(keys,None)}]}
    if style == 'morgan':value['column_groups']=[{'label':'1 Year','keys':keys[:3]},{'label':'YTD','keys':keys[3:]}]
    return value


class InstitutionalTables(unittest.TestCase):
    def test_templates_preserve_values_and_input_order(self):
        for style in ('morgan','blackstone','ibkr'):
            original=spec(style);snapshot=copy.deepcopy(original)
            for lang in ('en','zh'):
                rendered=Cells(build_html(original,lang))
                self.assertEqual(rendered.symbols,['LOW','HIGH','MISS'])
                expected=[(c['key'],row.get('values',{}).get(c['key'],row.get(c['key']))) for row in original['rows'] for c in original['columns']]
                self.assertEqual(rendered.values,expected)
            self.assertEqual(original,snapshot)

    def test_blackstone_parentheses_and_missing_not_zero(self):
        html=build_html(spec('blackstone'),'en')
        self.assertTrue('(8.7)%' in html)
        self.assertTrue('>NA<' in html)
        self.assertTrue('&lt;script&gt; &amp; Co' in html)

    def test_duplicate_columns_and_nonfinite_data_are_rejected(self):
        s=spec('ibkr');s['columns'].append(s['columns'][0])
        with self.assertRaisesRegex(ValueError,'unique'):build_html(s,'en')
        s=spec('ibkr');s['rows'][0]['values']['return']=float('nan')
        with self.assertRaisesRegex(ValueError,'finite'):build_html(s,'en')

    def test_morgan_group_headers_cannot_misalign_metrics(self):
        s=spec('morgan');s['column_groups'][1]['keys'].reverse()
        with self.assertRaisesRegex(ValueError,'column_groups'):build_html(s,'en')

    def test_existing_schwab_spec_and_dark_theme_still_work(self):
        s=json.loads((Path(__file__).resolve().parent.parent/'examples/watchlist_spec.json').read_text(encoding='utf-8'))
        html=build_html(s,'zh','dark')
        self.assertTrue('zh-Hant' in html and '收盤價' in html)

    def test_traditional_conversion_preserves_url_and_raw_data(self):
        html=traditional_html('<a href="资料/季度.html" data-id="股票">资料与净利润</a>')
        self.assertEqual(html,'<a href="资料/季度.html" data-id="股票">資料與淨利潤</a>')

    def test_price_templates_share_known_returns_and_prior_year_base(self):
        data={'end':'2026-01-02','series':{'A':{'points':[['2025-01-02',100],['2025-12-31',150],['2026-01-01',170],['2026-01-02',200]],'source':'test','fetched_at':'2026-01-03'}}}
        matrix=prepare(data,'morgan');grouped=prepare(data,'blackstone')
        self.assertEqual(matrix['rows'][0]['values'],grouped['rows'][0]['values'])
        values=matrix['rows'][0]['values']
        self.assertAlmostEqual(values['ytd_return'],(200/150-1)*100)
        self.assertAlmostEqual(values['year_return'],100)
        self.assertIsNone(values['year_vol'])          # sparse year history is not daily volatility
        self.assertEqual(matrix['calculation']['bases']['ytd']['A']['date'],'2025-12-31')

    def test_partial_fetch_and_zero_prices_cannot_become_performance(self):
        with self.assertRaisesRegex(ValueError,'fetch errors'):prepare({'errors':['failed']},'morgan')
        data={'end':'2026-01-02','series':{'A':{'points':[['2025-01-02',0],['2026-01-02',200]]}}}
        with self.assertRaisesRegex(ValueError,'positive'):prepare(data,'blackstone')
