---
name: schwab-performance-table
description: 把股票清單、券商持倉截圖或現成的漲跌幅/排名數據，做成 Charles Schwab 研報風格的業績表（排名表、持倉盈虧表、自選股表）；也能畫若干標的（最多 9 只）在任意時間段的走勢圖，含回撤、基準對比、對數刻度（中英雙語 PNG + HTML）。只要用戶提到業績表、持倉表、自選股表、走勢圖、漲幅對比、回撤，或要做研報風格的股票表格/圖、公衆號或 PPT 裏的股票配圖，就使用這個 skill，即使沒有明確提到 Schwab。
---

# Schwab 風格股票業績表

中文輸出一律預設繁體中文，包含圖表、名稱、表頭與腳註；`zh` 輸入鍵保持相容。

使用者指定摩根士丹利、黑石或 IBKR 報表時，先讀 [references/institutional-tables.md](references/institutional-tables.md)，依其實際用途準備字段。
Schwab 是原有預設；三個新增模板使用各自的報表結構，不會猜補持倉、市值、權重或研究觀點。

## 何時使用
用戶想把一組股票做成 Schwab 研報裏那種「淺藍標題表頭 + 灰色細分隔線 + 小字免責腳註」的表格。默認同時輸出**中文版和英文版**，每版一個 HTML，再用 Playwright 以 2x 渲染成 PNG。

要畫**走勢圖**（若干標的在某個時間段內的走勢）時，直接看文末的「走勢圖模式」。

## 第一步：判斷模式

| 模式 | 用戶給了什麼 | 標題 | 第 2–5 列 |
|---|---|---|---|
| A 排名表 | 每隻股票的 YTD 和 S&P 500 / NASDAQ 內排名（原版 Schwab 表） | `{年份} {組合名} Performance` / `{年份} 年{組合名}表現` | YTD (%)、S&P 500 Performance rank、S&P 500 Contribution rank、NASDAQ Performance rank |
| B 持倉表 | 券商持倉截圖或導出（成本、數量、盈虧） | `{年份} Portfolio Performance` / `{年份} 年持倉表現` | 開倉盈虧 (%)、當日盈虧 ($)、平均成本 ($)、持股數 |
| C 自選股表 | 只有一串股票代碼（如「NVDA AMD MU 做個表」） | `{年份} Watchlist Performance` / `{年份} 年自選股表現` | 年初至今 (%)、近 1 月 (%)、近 1 年 (%)、最新收盤價 ($) |

判斷不出來時問一句；用戶只報代碼、沒給任何數字，就是模式 C。

## 第二步：準備數據

### 通用規則
- 每隻股票必須有 `ticker`、英文全稱、中文通用名。沒有通用中文名的（如部分 ETF）中文版保留英文品牌名，可把描述詞譯出來（`Roundhill 新雲 ETF`）
- 所有數據必須是同一個截止日（`as_of`）。不同來源日期對不上時，統一到最早的那個共同日期，不要混用

### 模式 A
- 排名字段缺失時先問用戶；用戶確認沒有的填 `NA`
- 基準行：`NASDAQ`、`S&P 500`，三個排名列填 `NA`

### 模式 B（持倉截圖）
- 從截圖讀：代碼、開倉盈虧 %、當日盈虧、成本、數量；總計行的盈虧 %、當日盈虧；賬戶淨值、開倉盈虧金額（寫進腳註）
- 截圖裏的「交易價格」通常就是成本價，不是現價，不要當成現價
- 「組合合計」行擔任基準行角色：加粗、按盈虧 % 插入排序位置，成本和持股數填 `NA`
- `as_of`：截圖自帶時間戳時以它爲準。數字是盤中值（美東盤中截圖）就如實寫「as of {時間}，價格有延遲」，**不要寫成收盤日**；截圖沒有時間戳時，按標的所在交易所取最近收盤日；美股的臺北/北京上午截圖通常對應前一個美東交易日
- 合計行和各行對不上（可能含表外持倉或現金）時，**照券商原樣顯示，不要自行修正**；在腳註或回覆裏說明，並把你算出的差異告訴用戶

### 模式 C（只有代碼）
- 優先用 `fetch_prices.py` 取官方收盤價（比開瀏覽器快、可復現），`--start` 要早於一年多前纔算得出近 1 年，例如 `python3 fetch_prices.py NVDA AMD MU --start 2025-09-01 -o data/x.json`；再按下面的「數據源規定」自己計算 YTD、近 1 月、近 1 年回報。取不到時才退回 Claude in Chrome
- 用戶沒提基準就不加基準行；用戶要對比時，可用 `--benchmark SPY,COMP` 取基準，並說明 SPY 只是標普 500 的替代
- 股票超過 15 只時，先跟用戶確認是否全放，表格太長會失去研報感

## 數據源規定：官方優先，全球行情明確標註來源

「權威」指數據的**原始發佈方**，或者原樣轉載發佈方數據並註明出處的官方機構。美股保留 Nasdaq，滬深 A 股使用交易所官網；其他市場允許使用 Yahoo Finance 的免費日線，必須標註爲聚合行情，不能稱爲官方收盤價。

### 1. 允許的來源
| 數據 | 允許的來源 | 怎麼取 |
|---|---|---|
| 用戶自己的數據 | 用戶上傳的券商截圖、券商導出文件、券商官網頁面 | 直接用，不改寫 |
| 個股收盤價 | 上市交易所的官方收盤價：Nasdaq.com 歷史行情（含 NYSE 上市股票的綜合收盤價）、NYSE.com | 頁面是 JS 渲染，WebFetch 取不到，用 Claude in Chrome 打開 `https://www.nasdaq.com/market-activity/stocks/{ticker}/historical` 讀表 |
| 滬深 A 股日線 | 上交所 / 深交所官網後臺接口，未復權 | `fetch_prices.py 600519.SS 000001.SZ`；歷史不足時不得縮短區間冒充完整回報 |
| 全球股票日線 | Yahoo Finance 公共 chart 接口，聚合行情 | `fetch_prices.py 7203.T 0700.HK SAP.DE`；保留幣種、交易日期、抓取時間和來源 |
| 個股收盤價（備選） | 用戶的券商（如 Schwab 官網行情/研究頁，需用戶登錄） | Claude in Chrome |
| S&P 500 | S&P Dow Jones Indices；或 FRED 原樣轉載（序列 `SP500`，註明來源 S&P Dow Jones Indices） | WebFetch `https://fred.stlouisfed.org/series/SP500` |
| 納斯達克綜合指數 | Nasdaq Global Indexes；或 FRED 原樣轉載（序列 `NASDAQCOM`） | WebFetch `https://fred.stlouisfed.org/series/NASDAQCOM` |
| 拆股、公司正式名稱 | 公司 IR 公告、SEC EDGAR 文件 | WebFetch / WebSearch 限定官方域名 |
| 指數內排名（模式 A） | 只接受用戶提供（來自 Schwab、Bloomberg 等） | 不自己算 |

### 2. 禁止的來源
- ChartRow、stockanalysis.com、Google Finance、Investing.com、MarketBeat、Seeking Alpha、Stocktwits 等聚合站（實測 Google Finance 會給出過期價格）
- 論壇、博客、自動生成的 SEO 頁面、AI 摘要
- 模型記憶裏的任何數字
- 找不到權威來源時**不降級**到上述來源，改爲：停下來告訴用戶缺哪隻、缺什麼，請用戶提供（如從 Schwab 導出），或該格填 `NA` 並在回覆中說明

### 3. 由官方收盤價自己計算回報
網頁上現成的「YTD %」大多來自聚合站，不直接採用。統一用上述允許來源的收盤價計算，不採用網頁現成的百分比：
- **YTD** = 截止日收盤價 ÷ 上一年最後一個交易日收盤價 − 1
- **近 1 月** = 截止日收盤價 ÷ 一個月前同日收盤價 − 1（該日休市則取之前最近一個交易日）
- **近 1 年** = 同上，取一年前
- 計算區間內有拆股/合股的，按 IR 公告的比例調整舊價格
- Nasdaq 爲拆股調整後的價格回報；Yahoo 使用 `close`，不使用包含股息調整的 `adjclose`。滬深官網爲**未復權收盤價變動**，須提示除權事件可能影響結果；有拆股/配股等事件時先覈實公司公告，不得將未處理的結果稱爲復權投資回報。不同幣種默認按各自本幣計算，不自動換匯。
- 計算用代碼完成並保留原始收盤價，回覆裏附上用到的兩個價格，便於覈對

### 4. 截止日對齊
- 全表必須同一截止日，取所有來源都已更新到的最近一個交易日
- 某隻取不到該日官方收盤價，就從表裏拿掉並在回覆中說明，不用別的日期湊

### 5. 記錄
- 腳註寫原始發佈方，例如：`Source: Nasdaq (official closing prices), S&P Dow Jones Indices, Nasdaq Global Indexes via FRED, as of 10/2/2026. Returns are price returns calculated from official closing prices.`
- 回覆末尾列出每個數據頁面的鏈接

## 第三步：表格結構（自上而下 4 個區塊，5 列）

### 列
| # | 對齊 | 寬度 | 內容 |
|---|---|---|---|
| 1 | 左 | 30% | `{名稱} ({TICKER})`，表頭留空 |
| 2 | 右 | 13% | 主指標（排序依據） |
| 3–5 | 右 | 各 19% | 其餘指標 |

- **第 1 列必須帶股票代碼**，中英文版都要：`Micron Technology Inc (MU)`、`美光科技 (MU)`
- 基準行、合計行不帶代碼
- 名稱本身不再帶括號：寫 `谷歌 (GOOG)`，不寫 `Alphabet（谷歌）(GOOG)`

### 1. 標題行
- 淺藍底，與表頭是同一條連續色帶，中間無分隔線
- 加粗、深海軍藍，在整張表寬度上居中

### 2. 表頭（兩行）
- 底色同標題；加粗、深海軍藍、右對齊、底部對齊
- 第 1 行寫分組或修飾詞，第 2 行寫指標名和單位
- **每行都不能折行**，太長就拆成兩行。常用拆法：

| 英文 | 中文 |
|---|---|
| — / `YTD (%)` | `年初` / `至今 (%)` |
| `1-month` / `return (%)` | `近 1 月` / `漲跌幅 (%)` |
| `1-year` / `return (%)` | `近 1 年` / `漲跌幅 (%)` |
| `Last` / `price ($)` | `最新` / `收盤價 ($)` |
| `Open` / `P/L (%)` | `開倉` / `盈虧 (%)` |
| `Day` / `P/L ($)` | `當日` / `盈虧 ($)` |
| `Avg` / `cost ($)` | `平均` / `成本 ($)` |
| — / `Shares` | — / `持股數` |
| `S&P 500` / `Performance rank` | `標普 500` / `漲幅排名` |
| `S&P 500` / `Contribution rank` | `標普 500` / `貢獻排名` |
| `NASDAQ` / `Performance rank` | `納斯達克` / `漲幅排名` |

- 同幣種表格的單位只寫在表頭，單元格內不寫 `%` 或 `$`；跨幣種價格必須按行註明幣種，表頭去掉統一的 `$`

### 3. 數據區
- 白底；行間 1px 淺灰橫線，無豎線
- 全部行（股票 + 基準/合計）按第 2 列從高到低排序，基準行插在自己的位置上，不置頂也不置底
- 普通行常規字重、中灰；基準/合計行加粗、顏色更深
- 數字格式：百分比 1 位小數；金額 2 位小數加千分位；排名爲整數不加千分位；負數用 `-`，正數不加 `+`；持股數按原始精度
- 缺失值寫 `NA`

### 4. 腳註
- 表格下方，左對齊，與表同寬，小號灰字，自動換行
- 依次寫：來源與截止日 → 本表指標的定義 → 免責聲明 → 加粗的最後一句
- 模式 A 英文模板：

> Source: {source}, as of {as_of}. Performance rank based on performance within the respective index. Contribution rank (not available for NASDAQ) represents price performance multiplied by weight in index. All corporate names and market data shown above are for illustrative purposes only and are not a recommendation, offer to sell, or a solicitation of an offer to buy any security. Indexes are unmanaged, do not incur management fees, costs and expenses and cannot be invested in directly. **Past performance is no guarantee of future results.**

- 模式 B、C 把中間的指標定義換成本表的指標；沒有指數行時去掉「Indexes are unmanaged…」那句
- 中文版完整翻譯，最後一句爲加粗的「過往業績不代表未來表現。」

## 視覺參數（表寬 760px，取色爲估計值）
| 元素 | 值 |
|---|---|
| 英文/數字字體 | `Inter`，回退 `Helvetica Neue`, Helvetica, Arial |
| 中文字體 | `Noto Sans CJK TC` / `Source Han Sans TC`（思源黑體），回退 `PingFang TC`, `Microsoft JhengHei` |
| 數字列 | `font-feature-settings: "tnum" 1`（等寬數字）；負號單獨用 `"tnum" 0` 包住，避免出現 `- 8.56` |
| 標題/表頭底色 | `#ACDCEC` |
| 標題/表頭文字 | `#1B2A4A`；標題 15px / 700，表頭 13.5px / 600，行高 1.25 |
| 普通行 | `#595959`，13.5px，行高 26px |
| 基準/合計行 | `#2B2B2B`，600 |
| 行分隔線 | 1px `#D9D9D9` |
| 單元格內邊距 | 左 10px，右 12px |
| 外框 | 1px `#D0D0D0` |
| 腳註 | 英文 10px / 中文 10.5px，`#6B6B6B`，行高 1.4，上方留 7px |

## 第四步：渲染
1. 把數據寫成 spec JSON（格式見下）
2. 運行 `python3 render_table.py spec.json {輸出前綴}`，生成 `{前綴}_en.html/.png` 和 `{前綴}_zh.html/.png`
3. 打開兩張 PNG 對照自查清單，有問題改 spec 重渲
4. 交付兩張 PNG（HTML 一併給，方便改）

spec 格式：
```json
{
  "langs": {
    "en": {"title": "...", "h1": ["", "", "1-month", "1-year", "Last"],
           "h2": ["", "YTD (%)", "return (%)", "return (%)", "price ($)"],
           "foot": "Source: ... <b>Past performance is no guarantee of future results.</b>", "foot_size": "10px"},
    "zh": {"title": "...", "h1": [...], "h2": [...], "foot": "...<b>過往業績不代表未來表現。</b>", "foot_size": "10.5px"}
  },
  "formats": ["pct", "pct", "pct", "money"],
  "rows": [
    {"ticker": "NVDA", "name": {"en": "NVIDIA Corp", "zh": "英偉達"}, "cells": [25.7, 4.4, 24.2, 233.95]},
    {"name": {"en": "S&P 500", "zh": "標普 500"}, "cells": [12.8, null, null, null], "bench": true}
  ]
}
```
`formats`：`pct` 一位小數，`money` 兩位小數加千分位，`raw` 原樣輸出（排名、持股數用它）。`null` 顯示爲 `NA`。

可選參數：`--langs en` 只渲染指定語言；`--no-png` 只寫 HTML，不需要 Playwright；`--scale 3` 提高 PNG 清晰度（默認 2）。

沒有 `render_table.py` 時，按上面的結構和視覺參數手寫單文件 HTML，用 Playwright `device_scale_factor=2` 截 `#wrap` 容器。

## 自查清單
- [ ] 模式判斷正確，列與模式一致
- [ ] 中英文兩版都已輸出
- [ ] 每隻股票都帶 `(TICKER)`，基準/合計行不帶
- [ ] 所有數據來自允許來源；Yahoo 已標爲聚合行情，沒有模型記憶數字
- [ ] 所有數據同一截止日，腳註日期、來源、回報口徑正確
- [ ] 按第 2 列降序，基準/合計行在正確位置、加粗
- [ ] 表頭無折行；單元格無 `%`、`$`；負號無空隙
- [ ] 標題與表頭是一條連續淺藍色帶
- [ ] 腳註最後一句加粗
- [ ] 不畫原截圖左上角的「Legend」浮標（截圖殘留）

---

# 走勢圖模式：若干標的在歷史時間段內的走勢

## 何時使用
用戶要看一隻或多隻標的在某個時間段內的走勢、累計漲跌或回撤（例如「畫一下 NVDA、MU 今年的走勢」「這幾隻 3 月到 6 月的走勢對比」）。風格與業績表一致：淺藍標題帶、灰色細線、小字腳註，默認輸出**中文和英文兩版**（PNG + HTML）。最多 **9 只**標的，另可帶一條基準。

## 流程
1. **確定標的和時間段。** 用戶給了起止日就嚴格照用；沒說就是**年初至今**。起點取起始日當天或之前最近一個收盤價記爲 100（年初至今即上年最後一個交易日的收盤價）
2. **取數據**（自動按市場路由：美股 Nasdaq、滬深交易所官網、其他市場 Yahoo）：
   ```bash
   python3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 --end 2026-10-02 -o data/watch.json
   ```
   - 美股 Nasdaq 數據爲官方日收盤價，按拆股調整、不含股息，約有 10 年日線。其他市場的來源與復權限制見下方，不得套用同一官方來源說明。
   - 基準默認 **SPY**（標普 500 的 ETF，同一來源，圖和腳註會標明它只是指數的替代）。`--benchmark COMP` 用納斯達克綜合指數；`--benchmark SP500` 走 FRED 轉載的標普 500 指數（FRED 偶爾超時）；`--benchmark none` 不畫基準
   - 多個基準用逗號分隔：`--benchmark SPY,COMP`。`COMP`、`NDX` 等是指數，腳本直接按指數查（同樣的字母也可能是美股代碼，例如 COMP 是 Compass 公司）；代碼有歧義時用 `index:COMP`、`etf:SPY`、`stock:XXX` 指定類別
   - **全球代碼：** `7203.T`（東京）、`0700.HK`（香港）、`SAP.DE`（Xetra）、`600519.SS`（上海）、`000001.SZ`（深圳）。必須帶交易所後綴，裸數字代碼不猜市場；北交所暫不支持，需用戶 CSV。全球圖默認建議 `--benchmark none`，需要比較時再指定基準。
   - 滬深接口未復權，深交所歷史窗口有限；缺少起點收盤價會報錯，不會把截短區間畫成完整回報。Yahoo 是聚合來源，覆蓋與歷史長度因標的而異；當日尚未收盤的日線會排除。
   - **總回報：** Nasdaq 的分紅數據沒有按拆股調整，ETF 也沒有分紅，所以不能自動算總回報。用戶自己提供帶 `Adj Close` 的 CSV 時，用 `csv_to_prices.py --adj-close`，圖會標註爲總回報。價格回報和總回報不能畫在同一張圖裏
   - 響應緩存 12 小時（`--refresh` 繞過）。網絡失敗時會帶警告地用上一次緩存，腳註裏的獲取日期就是緩存實際獲取的日期
   - 只接受腳本返回的允許來源數據，不用其他聚合站或模型記憶數字。腳本以退出碼 2 結束、或 JSON 裏 `errors` 非空，說明有標的沒取到：**停下來告訴用戶缺哪隻**，不要自己補數
   - 公司名由 Claude 提供（英文全稱 + 通用中文名），寫進 spec 的 `names`
3. **寫 spec**（格式見下），運行：
   ```bash
   python3 render_chart.py spec.json out/watch
   ```
   生成 `out/watch_en.html/.png` 和 `out/watch_zh.html/.png`
4. 打開兩張 PNG，對照自查清單；有問題改 spec 重渲。交付兩張 PNG（HTML 一併給）

## 版式
| `layout` | 內容 | 適用 |
|---|---|---|
| `auto`（默認） | 5 只及以下用 `lines`，6–9 只用 `multiples` | 一般情況 |
| `lines` | 折線圖 + 回撤面板 + 彙總表 | 2–5 只 |
| `multiples` | 每隻一個小圖，**所有小圖同一縱軸**，每個小圖下帶回撤條，灰色虛線爲基準 | 6–9 只 |

- `y_scale`：`auto`（默認）、`linear`、`log`。`auto` 在最高與最低指數相差超過 3 倍時自動改用**對數刻度**，副標題會寫明「對數刻度」
- `drawdown`：是否畫回撤（默認開）；`table`：`lines` 版式是否帶彙總表（默認開）

## 規格
- 縱軸統一用「起點 = 100」的指數，**一張圖只有一個縱軸，不做雙軸**
- **顏色按標的固定順序，不隨排名變化**：藍 `#2a78d6`、橙 `#eb6834`、綠 `#1baf7a`、黃 `#eda100`、粉 `#e87ba4`（已通過色盲可分辨性檢查）。基準固定深灰虛線 `#595959`。小圖矩陣裏個股統一海軍藍 `#1B2A4A`，基準淺灰虛線
- 線寬 2px（基準 1.6px 虛線）；線尾畫圓點（2px 白圈），**線尾直接標註代碼和漲跌幅**，擠在一起時錯開並加小引線。綠、黃在白底上對比度偏低，所以直接標註和彙總表不能省
- 彙總表列：區間回報、年化波動率、最大回撤、最新價；按回報降序，基準行加粗，基準最新價填 `NA`
- 年化波動率 = 日價格回報的標準差 × √252；回撤 = 當日收盤價相對區間內至當日最高收盤價的跌幅；最大回撤 = 區間內回撤的最小值
- 腳註依次寫：來源與截止日、數據獲取日、起點、指標定義、基準替代說明（用 ETF 時）、免責聲明、加粗末句
- 時間跨度決定橫軸刻度：45 天內按周，約一年內按月，更長按季度或年

## spec 格式
```json
{
  "data": "data/watch.json",
  "symbols": ["NVDA", "MU"],
  "names": {"NVDA": {"en": "NVIDIA Corp", "zh": "英偉達"}, "MU": {"en": "Micron Technology Inc", "zh": "美光科技"}},
  "benchmark_name": {"en": "S&P 500 (SPY)", "zh": "標普 500 (SPY)"},
  "benchmarks": ["SPY", "COMP"], "colors": {"NVDA": "#2a78d6"},
  "layout": "auto", "y_scale": "auto", "drawdown": true, "table": true,
  "start": "2026-01-01", "end": "2026-10-02",
  "title": {"en": "...", "zh": "..."}, "note": {"en": "...", "zh": "..."}
}
```
除 `data` 外都是可選項。`start`、`end` 不寫時用數據文件的範圍；`note` 會放在腳註開頭（示例裏用來標註「虛構示例」）。`benchmarks` 選擇並排序數據文件裏的基準；`benchmark_name` 可以寫成 `{"en": ..., "zh": ...}`（用於第一個基準），也可以按代碼分別寫；`colors` 用 `#rrggbb` 覆蓋個別線條的顏色（默認配色已通過色盲可分辨性檢查，改色後自行保證對比度）。命令行參數：`--langs en` 只出一種語言，`--no-png` 只寫 HTML，`--pdf` 另存矢量 PDF，`--scale 3` 提高 PNG 清晰度（默認 2），`--theme dark` 輸出深色主題（表格和圖都支持）。HTML 文件裏鼠標懸停在圖上會顯示當天各條線的數值。

## 自查清單（走勢圖）
- [ ] 標的不超過 9 只；時間段與用戶要求一致（沒說就是年初至今）
- [ ] 數據來自 `fetch_prices.py` 的允許接口；Yahoo 來源、各幣種、各標的最後交易日和數據警告均如實顯示；缺失標的已告知用戶
- [ ] 中英文兩版都已輸出，腳註裏的來源、截止日、起點正確
- [ ] 只有一個縱軸；顏色按標的固定；線尾有直接標註，標籤不重疊、不被截斷
- [ ] 用 ETF 做基準時，腳註寫明它是替代；用對數刻度時，副標題寫明
- [ ] 彙總表按回報降序，基準行加粗，數字與線尾標註一致
- [ ] 滬深未復權風險已提示；Yahoo 未被稱爲官方來源；跨幣種漲跌幅註明未換匯；用戶 CSV 如實註明，總回報圖只用於用戶提供的股息調整價
