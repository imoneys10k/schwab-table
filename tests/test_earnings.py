import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from earnings_core import parse_period,point,subtract,report,change
from earnings_sources import sec_bundle,_rows,_number,_labelled_rows
from render_earnings import build_html


def bundle():
    source={'id':'official','url':'https://issuer.example/report','retrieved_at':'2026-10-08T00:00:00Z'}
    metrics={'revenue':point(200,'USD','2025-04-01','2025-06-30',['official']),
        'gross_profit':point(100,'USD','2025-04-01','2025-06-30',['official']),
        'cfo':point(60,'USD','2025-04-01','2025-06-30',['official']),
        'capex':point(20,'USD','2025-04-01','2025-06-30',['official'])}
    return {'symbol':'TEST','company_name':'Test <script> Co','currency':'USD','sources':[source],
        'quarters':{'FY2025Q3':{'start':'2025-04-01','end':'2025-06-30','metrics':metrics}}}


class EarningsArithmetic(unittest.TestCase):
    def test_time_variable_formats(self):
        for value in ('FY2025Q3','2025Q3','Q3FY2025','2025年第三季','2025年第3季度'):
            self.assertEqual(parse_period(value),'FY2025Q3')
        self.assertIsNone(parse_period('latest'))
        with self.assertRaises(ValueError):parse_period('第三季')
        with self.assertRaises(ValueError):parse_period('CY2025Q3')

    def test_cashflow_is_ytd_difference_with_both_sources(self):
        current=point(300,'USD','2025-01-01','2025-09-30',['q3'],fiscal_year=2025)
        previous=point(180,'USD','2025-01-01','2025-06-30',['q2'],fiscal_year=2025)
        derived=subtract(current,previous,'2025-07-01','2025-09-30')
        self.assertEqual(derived['value'],120);self.assertEqual(derived['source_ids'],['q3','q2'])
        self.assertEqual(len(derived['components']),2)
        self.assertIsNone(subtract(current,dict(previous,fiscal_year=2024),'2025-07-01','2025-09-30'))
        self.assertIsNone(subtract(current,dict(previous,end='2025-03-31'),'2025-07-01','2025-09-30'))

    def test_derived_ratios_and_fcf_do_not_mutate_imported_facts(self):
        facts=bundle();original=copy.deepcopy(facts);data=report(facts,'FY2025Q3')
        rows={r['key']:r for r in data['rows']}
        self.assertEqual(rows['gross_margin']['fact']['value'],50)
        self.assertEqual(rows['fcf']['fact']['value'],40)
        self.assertEqual(facts,original)
        self.assertEqual(rows['revenue']['view'],'unassessed')

    def test_negative_base_and_margin_percentage_points(self):
        a=point(-50,'USD',None,'2025-06-30',['a']);b=point(-100,'USD',None,'2024-06-30',['b'])
        value=change(a,b,'money');self.assertIsNone(value['value']);self.assertEqual(value['delta'],50)
        a=point(35,'%',None,'2025-06-30',['a']);b=point(30,'%',None,'2024-06-30',['b'])
        self.assertEqual(change(a,b,'pct')['value'],5)
        self.assertEqual(change(a,b,'pct')['unit'],'pp')

    def test_annual_values_and_wrong_units_cannot_be_a_quarter(self):
        facts=bundle();facts['quarters']['FY2025Q3']['metrics']['cfo']['start']='2025-01-01'
        with self.assertRaisesRegex(ValueError,'cumulative'):report(facts,'FY2025Q3')
        facts=bundle();facts['quarters']['FY2025Q3']['metrics']['revenue']['unit']='EUR'
        with self.assertRaisesRegex(ValueError,'currency'):report(facts,'FY2025Q3')

    def test_missing_report_period_is_not_substituted(self):
        with self.assertRaisesRegex(ValueError,'substituted'):report(bundle(),'FY2025Q2')

    def test_flow_with_no_period_start_cannot_be_treated_as_quarterly(self):
        facts=bundle();facts['quarters']['FY2025Q3']['metrics']['revenue']['start']=None
        with self.assertRaisesRegex(ValueError,'start date'):report(facts,'FY2025Q3')

    def test_pdf_layout_and_dashes_are_not_guessed_as_zero(self):
        self.assertIsNone(_number('—'));self.assertEqual(_number('0'),0)
        self.assertEqual(_rows('Revenue      $ 1,200      $ (300)'),[('Revenue',[1200,-300])])

    def test_first_quarter_pdf_has_two_columns_and_kerning_keeps_tokens(self):
        text='Total net sales (1) 124,300 119,575 Net income $ 36,330 $ 33,916'
        self.assertEqual(_labelled_rows(text,['Total net sales (1)','Net income'],2),
            [('Total net sales (1)',[124300,119575]),('Net income',[36330,33916])])
        self.assertEqual(_labelled_rows('N e t i n c o m e $ 10,000 $ 9,000 $ 30,000 $ 27,000', ['Net income'],4),
            [('Net income',[10000,9000,30000,27000])])

    def test_hsbc_render_preserves_missing_trend_and_escapes_text(self):
        html=build_html(report(bundle(),'FY2025Q3'))
        self.assertTrue('zh-Hant' in html and '&lt;script&gt;' in html)
        self.assertTrue('data-view="unassessed"' in html and '資料不足' in html)


class SECFiscalPeriods(unittest.TestCase):
    def facts(self):
        data={'cik':999,'entityName':'Fixture','facts':{'us-gaap':{}}}
        tags=data['facts']['us-gaap']
        def add(tag,acc,fy,fp,start,end,value,unit='USD'):
            row={'accn':acc,'fy':fy,'fp':fp,'form':'10-K' if fp=='FY' else '10-Q','filed':'2025-11-01' if fp=='FY' else '2025-08-01','end':end,'val':value}
            if start:row['start']=start
            tags.setdefault(tag,{'units':{}})['units'].setdefault(unit,[]).append(row)
        for acc,fp,end in [('q3','Q3','2025-06-30'),('fy','FY','2025-09-30')]:
            add('Assets',acc,2025,fp,None,end,500)
        add('RevenueFromContractWithCustomerExcludingAssessedTax','q3',2025,'Q3','2025-04-01','2025-06-30',30)
        add('RevenueFromContractWithCustomerExcludingAssessedTax','q3',2025,'Q3','2024-10-01','2025-06-30',90)
        add('RevenueFromContractWithCustomerExcludingAssessedTax','fy',2025,'FY','2024-10-01','2025-09-30',140)
        for tag,v3,v4 in [('NetCashProvidedByUsedInOperatingActivities',70,110),('PaymentsToAcquirePropertyPlantAndEquipment',20,30)]:
            add(tag,'q3',2025,'Q3','2024-10-01','2025-06-30',v3);add(tag,'fy',2025,'FY','2024-10-01','2025-09-30',v4)
        add('EarningsPerShareDiluted','q3',2025,'Q3','2024-10-01','2025-06-30',2.7,'USD/shares')
        add('EarningsPerShareDiluted','fy',2025,'FY','2024-10-01','2025-09-30',4.2,'USD/shares')
        return data

    def test_q4_uses_fy_minus_nine_months_and_never_subtracts_eps(self):
        with patch('earnings_sources.fetch',return_value=(json.dumps(self.facts()).encode(),{'retrieved_at':'2026-10-08T00:00:00Z'})):
            facts,period=sec_bundle('TEST','FY2025Q4',999)
        rows={r['key']:r for r in report(facts,period)['rows']}
        self.assertEqual(facts['quarters'][period]['start'],'2025-07-01')
        self.assertEqual(rows['revenue']['fact']['value'],50)
        self.assertEqual(rows['cfo']['fact']['value'],40)
        self.assertEqual(rows['fcf']['fact']['value'],30)
        self.assertIsNone(rows['eps']['fact'])
