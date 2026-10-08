---
name: quarterly-earnings-review
description: 解讀指定股票與財季的季度財報，核對單季、同比、環比及業務驅動，輸出 HSBC 風格研究表（繁體中文與英文 PNG/HTML）及來源臺帳。用於「幫我看看2025第三季AAPL財報怎麼樣」「用匯豐表分析time的XXXX財報」等季度解讀；不替代完整估值、買賣建議或一般股價走勢分析。
---

# 季度財報與市場研究

使用者提供股票代碼與時間；先核對原始財報，再用 HSBC 資產觀點矩陣版式呈現「財務項目／同比趨勢／研究評論」。預設繁體中文及英文，寫明實際財季起訖日。

## 股票與時間

- 把 XXXX 換成實際股票代碼，把 time 換成年度及季度。
- 未限定自然季時，按公司所披露財季解讀，顯示 FY2025Q3 及實際日期。Apple FY2025Q3 是 2025-03-30～2025-06-28，不能標成2025年7～9月。
- 沒有時間時取最新已披露財報，核對公司IR發布記錄。只說第三季未給年份時確認年份；明確指定自然季／日期區間時查證對應披露，不能硬套公司財季。
- 年報、半年報與季度數據不能互換；沒有對應原件時明說未取得，不換成其他期間。

## 取得與核對

1. 執行本技能腳本，先取得事實與臺帳：

   ```bash
   python3 <skill_dir>/scripts/review.py AAPL --period FY2025Q3 -o out/aapl_q3 --no-png
   ```

   腳本隨本專案使用。複製安裝的 Skill 從 `project.json` 讀所屬專案路徑；使用該專案 `.venv/bin/python`（Windows為 `.venv/Scripts/python.exe`）執行，或以已安裝依賴的 Python 執行。AAPL讀Apple官方財務PDF；其他US-GAAP 10-Q/10-K公司使用SEC Company Facts，必要時提供核實的 --cik。SEC請求可設定 SEC_USER_AGENT；快取12小時，保留取得時間，網路拒絕時不補造資料。依賴在所屬專案以 `pip install -r requirements.txt` 安裝。

2. 讀 _facts.json、_audit.json，打開來源文件核對期間、幣別、單位與數字。重要不變條件見 [references/financial-review.md](references/financial-review.md)。SEC的fy/fp是申報焦點，前期比較數據也可能帶當期fy；實際日期不可省略。

3. API不覆蓋的公司，讀公司IR／上市交易所公告或使用者報表，按 [references/facts-schema.md](references/facts-schema.md) 整理帶來源的單季資料，用 --facts verified.json。Yahoo股價不能充當財報；來源、比較期或數值缺失保留NA。

## 回答「這季財報怎麼樣」

給一段結論，說明數據支持與限制。從原件選擇有意義的驅動：產品／地區收入結構、利潤率、EPS與股本、現金轉換、資本投入、管理層對需求與成本的說法。現金流與EPS不同步時分別解釋，不能只看EPS。

市場研究用公司披露及可比公司的同期間原件。沒有發布前一致預期時不說超／低於預期；沒有對齊公告時點的事件行情，不把季內漲跌當財報反應。指引、研究判斷與已實現數字分開。新增官方公告／法說來源先閱讀原件，再加入事實臺帳 sources；評論只能引用臺帳ID。

用模型撰寫 analysis.json，新增解讀但不覆蓋財務事實：

```json
{
  "source_ids":["apple-FY2025Q3","apple-FY2025Q2"],
  "overview":{"zh":"結論與主要證據……","en":"Conclusion and evidence..."},
  "comments":{
    "revenue":{"zh":"收入驅動與限制……","en":"Revenue drivers and limits..."},
    "fcf":{"zh":"現金流與資本投入的變化……","en":"Cash flow and investment..."}
  }
}
```

重新輸出帶研究評論的表：

```bash
python3 <skill_dir>/scripts/review.py AAPL --period FY2025Q3 --facts out/aapl_q3_facts.json --analysis analysis.json -o out/aapl_q3
```

## 交付

檢查中英文PNG的文字、單位、引用與三角含義。給繁體PNG／HTML，英文一併附上；簡短說明財季日期、結論及關鍵缺失。來源可點擊，原始_facts.json與推導／比較_audit.json保留以供核對，不把技術臺帳全文塞進圖中。不聲稱是HSBC出具的研報或投資評級。
