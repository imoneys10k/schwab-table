# 已核實事實匯入

`--facts verified.json` 用於官方IR、交易所或使用者提供報表整理的單季事實，不以股價、年度值或記憶補空。

```json
{
  "symbol":"AAPL", "company_name":"Apple Inc.", "currency":"USD",
  "sources":[{"id":"issuer-q3", "title":"Official quarterly statement",
    "url":"https://www.apple.com/newsroom/pdfs/fy2025-q3/FY25_Q3_Consolidated_Financial_Statements.pdf",
    "retrieved_at":"2026-10-08T00:00:00Z", "kind":"company_ir"}],
  "quarters":{"FY2025Q3":{"start":"2025-03-30", "end":"2025-06-28",
    "metrics":{
      "revenue":{"value":94036000000, "unit":"USD", "start":"2025-03-30", "end":"2025-06-28",
        "source_ids":["issuer-q3"], "method":"reported", "page":1},
      "eps":{"value":1.57, "unit":"USD/shares", "start":"2025-03-30", "end":"2025-06-28",
        "source_ids":["issuer-q3"], "method":"reported", "page":1}
    }}}
}
```

這是格式示例，實際需記錄真實取得時間、完整核對數據與比較期。同比加入FY2024Q3，環比加入FY2025Q2，各自有實際日期。
缺失省略或null，不填零。時點欄start可null，但end須為該季度末。台帳中每個來源需URL或原檔路徑及取得時間。

核心字段：revenue、gross_profit、operating_income、net_income、eps、cfo、capex、rd、cash、debt、assets、equity。
gross_margin、operating_margin、net_margin、fcf可由明確組成項推導。capex用正支出額；money用基礎幣別單位。
產品／地域字段：iphone、mac、ipad、wearables、services、greater_china；其他公司業務拆分用來源支持的研究評論，不硬套Apple產品名。

analysis.json只能新增overview與comments，不覆蓋事實；新增官方研究來源先加入原始台帳，再引用其ID。
