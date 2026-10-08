# HSBC 季度財報研究（本機開發版）

輸入股票代碼與公司財季，輸出 HSBC 矩陣版式的財報解讀：繁體中文／英文 HTML 與 PNG，另附原始事實和計算臺帳。這項功能位於 `feature/quarterly-earnings-review` 本機分支，未推送，也不包含在公開 v0.5.0 發布中。

## 使用

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
python3 quarterly_earnings.py AAPL --period FY2025Q3 -o out/aapl_q3
```

`FY2025Q3`、`2025Q3`、`2025年第三季` 按公司財季解析；Apple 此財季的實際日期為 2025-03-30 至 2025-06-28。省略時間則核對最新已披露財季。明確要求自然季時須查證映射，不會將公司財季換標為自然季。

安裝的 Skill 為 [quarterly-earnings-review](skills/quarterly-earnings-review/SKILL.md)，可用「幫我看看 FY2025Q3 的 AAPL 財報，用 HSBC 表」觸發。Skill 先取得官方數據、讀來源原件，再編寫研究評論。單獨執行腳本會產生數據表；加入 `--analysis analysis.json` 才附上來源支持的研究解讀。

## 來源與計算

- AAPL：Apple 官方季度財務 PDF。已用 FY2025Q3、FY2025Q4 真實原件端到端驗證；先核對報表標題、欄位數、單位與日期，再讀取對應行。
- 其他 US-GAAP 公司：SEC Company Facts，必要時傳入已核實的 `--cik`。這台機器對 SEC 自動請求回傳 403，因此 SEC 解析／第四季推導已以固定測試資料驗證，尚未通過本機即時取數驗證。可設定合規的 `SEC_USER_AGENT`，或者匯入核實的官方財報事實。
- 其他市場：閱讀公司 IR／交易所原件，按 [事實格式](skills/quarterly-earnings-review/references/facts-schema.md) 匯入 `--facts verified.json`。本版沒有宣稱全球財報自動覆蓋。
- 原始來源保留 URL、取得時間與 SHA256；快取 12 小時。無法取得指定季度時回報失敗，不改用另一季度、不捏造數字。
- 現金流按單季拆分；累計相減必須屬同一財年且期間銜接。全年減九個月可推導第四季金額，但不能直接相減 EPS。利潤率比較用百分點；比較基期非正值時不計百分比。缺失資料保留 NA。
- 原始事實不被分析文字覆蓋。評論須引用來源臺帳 ID；未取得一致預期時不宣稱超／低於預期。

## 可重現示例

`examples/earnings/` 保存兩個 Apple 財季的官方事實快照及研究評論。離線重建：

```bash
python3 quarterly_earnings.py AAPL --period FY2025Q3 --facts examples/earnings/aapl_2025q3_facts.json --analysis examples/earnings/aapl_2025q3_analysis.json -o out/aapl_2025q3
python3 quarterly_earnings.py AAPL --period FY2025Q4 --facts examples/earnings/aapl_2025q4_facts.json --analysis examples/earnings/aapl_2025q4_analysis.json -o out/aapl_2025q4
```

第三季示例區分盈利增長與自由現金流減少；第四季示例解釋上年一次性愛爾蘭稅項對 GAAP 同比基期的影響，保留 GAAP 數字與非 GAAP 解釋的界線。每個示例含 22 項指標、同比／環比、業務分項及來源。版式沿用先前核對的 HSBC 三欄灰底分組矩陣，沒有聲稱是 HSBC 出具的研究報告。

## 驗證

```bash
python3 -m unittest discover -s tests -v
```

本機 58 項測試通過；兩個 Apple 真實財季的數字與拆季計算核對通過。四張中英文表完成瀏覽器檢查，離線預覽完成季度／語言切換與窄螢幕檢查。來源／期間規則見 [financial-review.md](skills/quarterly-earnings-review/references/financial-review.md)。
