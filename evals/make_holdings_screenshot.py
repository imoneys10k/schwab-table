import asyncio
from playwright.async_api import async_playwright
rows = [  # symbol, name, qty, trade price (= average cost), day $, open P/L %, open P/L $
 ("NVDA", "NVIDIA CORP", 300, 118.40, 612.00, 101.8, 30123.0),
 ("MU", "MICRON TECHNOLOGY INC", 40, 287.50, -1120.40, 270.1, 31060.0),
 ("AAPL", "APPLE INC", 150, 245.10, 331.50, 35.8, 13165.0),
 ("META", "META PLATFORMS INC CL A", 25, 698.20, -212.75, 6.2, 1085.0),
 ("TSLA", "TESLA INC", 60, 392.00, 540.00, -31.4, -7387.0),
]
tr = "".join(f"<tr><td class=s>{s}</td><td>{n}</td><td>{q}</td><td>${p:,.2f}</td><td class='{'g' if d>=0 else 'r'}'>{'+' if d>=0 else '-'}${abs(d):,.2f}</td><td class='{'g' if o>=0 else 'r'}'>{'+' if o>=0 else '-'}{abs(o):.1f}%</td><td class='{'g' if u>=0 else 'r'}'>{'+' if u>=0 else '-'}${abs(u):,.2f}</td></tr>" for s,n,q,p,d,o,u in rows)
html = f"""<html><body style="margin:0;font-family:Arial,Helvetica,sans-serif;background:#fff"><div style="width:980px;padding:20px">
<div style="font-size:22px;color:#00A0DF;font-weight:700">Positions · Individual Brokerage ****4821</div>
<div style="margin:6px 0 14px;color:#555;font-size:13px">As of 10/05/2026 09:41 AM ET · Prices delayed</div>
<table style="border-collapse:collapse;width:100%;font-size:14px"><thead><tr style="background:#f0f3f6;text-align:left">
<th style="padding:8px">Symbol</th><th>Description</th><th>Qty</th><th>Trade Price</th><th>Day Chg $</th><th>Open P/L %</th><th>Open P/L $</th></tr></thead><tbody>{tr}
<tr style="font-weight:700;background:#f7f9fb"><td class=s>Total</td><td></td><td></td><td></td><td class=r>-$461.65</td><td class=g>+23.4%</td><td class=g>+$67,990.63</td></tr></tbody></table>
<div style="margin-top:16px;font-size:15px;font-weight:700">Account Value: $358,420.17 &nbsp;·&nbsp; Total Open P/L: +$67,990.63</div></div>
<style>td{{padding:9px 8px;border-bottom:1px solid #e3e7ea}} .s{{font-weight:700}} .g{{color:#0a8a3a}} .r{{color:#c62828}}</style></body></html>"""
async def m():
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(device_scale_factor=2, viewport={"width":1020,"height":500})
        await pg.set_content(html); await pg.screenshot(path="holdings_screenshot.png", full_page=True); await b.close()
asyncio.run(m())
