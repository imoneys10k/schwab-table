"""Deterministic fictional-company examples for three institutional templates."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
STOCKS=[
('ACRB','Acme Robotics','極客機器人','tech',88.4,143.2,194.35),
('HOOL','Hooli Cloud','呼哩雲','tech',22.3,35.0,127.55),
('CYDN','Cyberdyne Systems','賽博系統','tech',14.5,21.6,84.30),
('INSY','Initech Systems','因尼科技','tech',-5.2,-11.6,39.90),
('STRK','Stark Aerospace','星銳航天','industrial',41.7,62.9,312.80),
('MDSY','Meridian Industrial','經緯工業','industrial',19.8,27.4,76.65),
('STLG','Stride Logistics','遠行物流','industrial',6.9,12.8,42.18),
('NVAT','Nova Automation','新星自動化','industrial',-8.7,-4.8,28.75),
('RVFN','Riverstone Financial','磐石金融','financial',12.2,18.5,63.92),
('SMAS','Summit Assurance','峰頂保險','financial',9.5,16.2,105.40),
('OAKB','Oak Bancorp','橡樹銀行','financial',4.7,6.8,33.15),
('HBCA','Harbor Capital','海港資本','financial',-3.6,-7.9,52.80)]
GROUPS={'tech':{'en':'TECHNOLOGY','zh':'科技'},'industrial':{'en':'INDUSTRIALS','zh':'工業'},'financial':{'en':'FINANCIALS','zh':'金融'}}
FOOT={'en':'Source: synthetic sample data, as of 7 October 2026. All companies, symbols, returns, risk metrics and holdings are fictional. Returns exclude dividends; values are USD. Missing values are NA. Not a report issued by the referenced institution. <b>Past performance is no guarantee of future results.</b>',
 'zh':'資料來源：合成示例數據，截至2026年10月7日。公司、代碼、回報、風險指標及持倉均為虛構；回報不含股息，市值以美元表示，缺失值填NA。本表並非相關機構出具的研究報告。<b>過往業績不代表未來表現。</b>'}


def main():
    rows=[]
    for i,(symbol,en,zh,group,ytd,year,price) in enumerate(STOCKS):
        rows.append({'ticker':symbol,'name':{'en':en,'zh':zh},'group':GROUPS[group],'level':2,
            'values':{'ytd_return':ytd,'ytd_vol':round(22+i*1.7,1),'ytd_drawdown':round(-12-i*1.1,1),
                      'year_return':year,'year_vol':round(26+i*1.8,1),'year_drawdown':round(-18-i*1.2,1)}})
    cols=[{'key':'name','label':{'en':'','zh':''},'width':29.44}]
    for prefix in ('ytd','year'):
        for key,en,zh in [('return','Return\n(%)','回報\n(%)'),('vol','Annualized\nvolatility (%)','年化\n波動率 (%)'),('drawdown','Max drawdown\n(%)','最大回撤\n(%)')]:
            cols.append({'key':prefix+'_'+key,'label':{'en':en,'zh':zh},'format':'pct','width':11.76})
    morgan={'style':'morgan','columns':cols,'rows':rows,'column_groups':[
        {'label':{'en':'YTD\nAS OF 7 OCTOBER 2026','zh':'年初至今\n截至2026年10月7日'},'keys':[c['key'] for c in cols[1:4]]},
        {'label':{'en':'TRAILING YEAR\nAS OF 7 OCTOBER 2026','zh':'近一年\n截至2026年10月7日'},'keys':[c['key'] for c in cols[4:]]}],
        'langs':{l:{'title':'Equity Return and Risk Estimates' if l=='en' else '股票回報與風險指標','foot':FOOT[l]} for l in ('en','zh')}}
    blackstone={'style':'blackstone','columns':[dict(cols[0],width=52),
        {'key':'ytd_return','label':{'en':'YTD','zh':'年初至今'},'format':'pct','width':24},
        {'key':'year_return','label':{'en':'Trailing 1Y','zh':'近一年'},'format':'pct','width':24}],
        'rows':rows,'langs':{l:{'title':'Investment Performance' if l=='en' else '投資業績',
            'subtitle':'(price appreciation / excluding dividends)' if l=='en' else '（價格變動／不含股息）','foot':FOOT[l]} for l in ('en','zh')}}
    holdings=[];long_total=short_total=0
    for i,(symbol,en,zh,group,ytd,year,price) in enumerate(STOCKS):
        long=round(price*(150+i*20),2) if i!=3 else 0.0
        short=round(-price*80,2) if i==3 else 0.0
        long_total+=long;short_total+=short
        holdings.append({'ticker':symbol,'name':{'en':en.upper(),'zh':zh},'sector':GROUPS[group],
            'values':{'long':long,'short':short,'net':round(long+short,2)}})
    net_total=long_total+short_total
    for row in holdings:
        v=row['values'];v.update(long_weight=v['long']/long_total*100,
            short_weight=v['short']/short_total*100,net_weight=v['net']/net_total*100)
    fields=[('ticker','Symbol','代碼',None,12),('name','Description','證券名稱',None,23),('sector','Sector','行業',None,8),
        ('long','Long Value','多頭市值','money',9),('short','Short Value','空頭市值','money',9),('net','Net Value','淨市值','money',9),
        ('long_weight','Long Weight %','多頭權重 %','pct',10),('short_weight','Short Weight %','空頭權重 %','pct',10),('net_weight','Net Weight %','淨權重 %','pct',10)]
    ibkr={'style':'ibkr','as_of':{'en':'As of: 7 October 2026','zh':'截至：2026年10月7日'},
        'columns':[{'key':key,'label':{'en':en,'zh':zh},'format':fmt or 'text','width':width} for key,en,zh,fmt,width in fields],
        'rows':holdings,'langs':{l:{'title':'Concentration' if l=='en' else '集中度','section':'Holdings' if l=='en' else '持倉明細',
            'exposure_title':'Exposure' if l=='en' else '敞口','foot':FOOT[l]+(' Long and short weights use their respective gross totals; net weight uses net value. Weights are position values, not derivative look-through exposure.' if l=='en' else '多頭與空頭權重分別以各自總市值計算；淨權重以淨市值計算。權重為部位市值，並非衍生品穿透敞口。')} for l in ('en','zh')},
        'exposure':[{'columns':[{'key':'name','label':{'en':'Exposure','zh':'敞口'},'width':50},{'key':'value','label':{'en':'Value (USD)','zh':'市值（USD）'},'format':'money','width':50}],
            'rows':[{'name':{'en':'Long','zh':'多頭'},'values':{'value':long_total}},{'name':{'en':'Short','zh':'空頭'},'values':{'value':short_total}},{'name':{'en':'Net','zh':'淨敞口'},'values':{'value':net_total}}]}]}
    for key,spec in [('morgan',morgan),('blackstone',blackstone),('ibkr',ibkr)]:
        (ROOT/f'{key}_spec.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
