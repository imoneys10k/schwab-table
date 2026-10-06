# Schwab-style stock performance table

> English translation of [SKILL.md](SKILL.md). `SKILL.md` (Chinese) is the file Claude loads and the source of truth; if the two ever differ, `SKILL.md` wins.

## When to use
The user wants to turn a set of stocks into the kind of table found in Schwab research: a light-blue title/header band, thin grey row dividers, and a small-print disclaimer footnote. By default, output **both a Chinese and an English version**, one HTML file each, then render each to PNG with Playwright at 2x.

## Step 1: Identify the mode

| Mode | What the user provides | Title | Columns 2–5 |
|---|---|---|---|
| A. Ranking table | Each stock's YTD return and its rank within the S&P 500 / NASDAQ (the original Schwab table) | `{year} {portfolio name} Performance` / `{年份} 年{组合名}表现` | YTD (%), S&P 500 Performance rank, S&P 500 Contribution rank, NASDAQ Performance rank |
| B. Holdings table | A brokerage holdings screenshot or export (cost, quantity, P/L) | `{year} Portfolio Performance` / `{年份} 年持仓表现` | Open P/L (%), Day P/L ($), Avg cost ($), Shares |
| C. Watchlist table | Only a list of tickers (e.g. "make a table for NVDA AMD MU") | `{year} Watchlist Performance` / `{年份} 年自选股表现` | YTD (%), 1-month (%), 1-year (%), Last price ($) |

If the mode is unclear, ask one question. If the user gives only tickers and no numbers, it is mode C.

## Step 2: Prepare the data

### General rules
- Every stock needs a `ticker`, an English full name and a common Chinese name. If there is no common Chinese name (e.g. some ETFs), keep the English brand name in the Chinese version and translate only the descriptive words (`Roundhill 新云 ETF`)
- All data must share one cutoff date (`as_of`). If sources disagree on dates, align to the earliest common date; never mix dates

### Mode A
- If rank fields are missing, ask the user first; fill `NA` for anything the user confirms does not exist
- Benchmark rows: `NASDAQ`, `S&P 500`, with `NA` in the three rank columns

### Mode B (holdings screenshot)
- Read from the screenshot: ticker, open P/L %, day P/L, cost, quantity; the total row's P/L % and day P/L; account value and open P/L amount (these go in the footnote)
- The "trade price" in a screenshot is usually the cost basis, not the current price; do not treat it as the current price
- The "portfolio total" row plays the benchmark role: bold, inserted at its sorted position by P/L %, with cost and shares set to `NA`
- `as_of` is the **most recent US market close** matching the screenshot (a Taipei/Beijing morning screenshot = the previous US Eastern trading day)

### Mode C (tickers only)
- Claude fetches official closing prices per the "Data-source rules" below and computes YTD, 1-month and 1-year returns itself
- With more than 15 stocks, confirm with the user first whether to include them all; a table that long loses the research-note look

## Data-source rules: authoritative data only

"Authoritative" means the **original publisher** of the data, or an official body that republishes the publisher's data verbatim with attribution. Aggregator sites, quote apps and finance blogs never count.

### 1. Allowed sources
| Data | Authoritative source | How to get it |
|---|---|---|
| The user's own data | Brokerage screenshots, exports or web pages the user provides | Use as given; do not rewrite |
| Stock closing prices | The listing exchange's official close: Nasdaq.com historical quotes (including consolidated closes for NYSE-listed stocks), NYSE.com | The page is JS-rendered, so WebFetch cannot read it; open `https://www.nasdaq.com/market-activity/stocks/{ticker}/historical` in Claude in Chrome and read the table |
| Stock closing prices (fallback) | The user's brokerage (e.g. Schwab quote/research pages; requires the user to be logged in) | Claude in Chrome |
| S&P 500 | S&P Dow Jones Indices; or FRED republishing it verbatim (series `SP500`, credited to S&P Dow Jones Indices) | WebFetch `https://fred.stlouisfed.org/series/SP500` |
| Nasdaq Composite | Nasdaq Global Indexes; or FRED (series `NASDAQCOM`) | WebFetch `https://fred.stlouisfed.org/series/NASDAQCOM` |
| Splits, official company names | Company IR announcements, SEC EDGAR filings | WebFetch / WebSearch restricted to official domains |
| Rank within an index (mode A) | Only accepted from the user (from Schwab, Bloomberg, etc.) | Never computed by Claude |

### 2. Forbidden sources
- Aggregators such as ChartRow, stockanalysis.com, Yahoo Finance, Google Finance, Investing.com, MarketBeat, Seeking Alpha, Stocktwits (Google Finance was observed to return stale prices)
- Forums, blogs, auto-generated SEO pages, AI summaries
- Any number from the model's memory
- When no authoritative source can be found, **do not fall back** to the above. Instead: stop and tell the user which ticker and what is missing and ask them to supply it (e.g. a Schwab export), or fill that cell with `NA` and say so in the reply

### 3. Compute returns yourself from official closes
Ready-made "YTD %" figures on web pages mostly come from aggregators and are not used directly. Always compute from official closing prices:
- **YTD** = close on the cutoff date ÷ close on the last trading day of the previous year − 1
- **1-month** = close on the cutoff date ÷ close on the same day one month earlier − 1 (if that day was a market holiday, use the nearest earlier trading day)
- **1-year** = same, one year earlier
- If a split or reverse split falls inside the window, adjust the older prices by the ratio in the IR announcement
- The basis is always **price return** (excluding dividends), consistent with the S&P 500 and Nasdaq Composite
- Do the computation in code, keep the raw closing prices, and include the two prices used in the reply so they can be checked

### 4. Cutoff alignment
- The whole table must share one cutoff date: the most recent trading day for which all sources are updated
- If one stock has no official close for that date, drop it from the table and say so in the reply; do not patch with another date

### 5. Record keeping
- The footnote names the original publisher, e.g.: `Source: Nasdaq (official closing prices), S&P Dow Jones Indices, Nasdaq Global Indexes via FRED, as of 10/2/2026. Returns are price returns calculated from official closing prices.`
- End the reply with a link to each data page used

## Step 3: Table structure (4 blocks from top to bottom, 5 columns)

### Columns
| # | Alignment | Width | Content |
|---|---|---|---|
| 1 | Left | 37% | `{name} ({TICKER})`; header left blank |
| 2 | Right | 15% | Primary metric (the sort key) |
| 3–5 | Right | 16% each | Remaining metrics |

- **Column 1 must include the ticker**, in both language versions: `Micron Technology Inc (MU)`, `美光科技 (MU)`
- Benchmark and total rows carry no ticker
- The name itself must not contain extra parentheses: write `谷歌 (GOOG)`, not `Alphabet（谷歌）(GOOG)`

### 1. Title row
- Light-blue background, one continuous band with the header, no divider between them
- Bold, deep navy, centred across the full table width

### 2. Header (two rows)
- Same background as the title; bold, deep navy, right-aligned, bottom-aligned
- Row 1 holds the group or a modifier word; row 2 holds the metric name and unit
- **Neither row may wrap**; if too long, split across the two rows. Common splits:

| English | Chinese |
|---|---|
| — / `YTD (%)` | `年初` / `至今 (%)` |
| `1-month` / `return (%)` | `近 1 月` / `涨跌幅 (%)` |
| `1-year` / `return (%)` | `近 1 年` / `涨跌幅 (%)` |
| `Last` / `price ($)` | `最新` / `收盘价 ($)` |
| `Open` / `P/L (%)` | `开仓` / `盈亏 (%)` |
| `Day` / `P/L ($)` | `当日` / `盈亏 ($)` |
| `Avg` / `cost ($)` | `平均` / `成本 ($)` |
| — / `Shares` | — / `持股数` |
| `S&P 500` / `Performance rank` | `标普 500` / `涨幅排名` |
| `S&P 500` / `Contribution rank` | `标普 500` / `贡献排名` |
| `NASDAQ` / `Performance rank` | `纳斯达克` / `涨幅排名` |

- Units appear only in the header; cells never contain `%` or `$`

### 3. Data area
- White background; 1px light-grey horizontal rules between rows, no vertical lines
- All rows (stocks plus benchmark/total) sorted by column 2, high to low; benchmark rows sit at their sorted position, neither pinned to the top nor the bottom
- Normal rows: regular weight, mid-grey; benchmark/total rows: bold, darker
- Number formats: percentages to 1 decimal; money to 2 decimals with thousands separators; ranks are integers without thousands separators; negatives use `-`, positives carry no `+`; share counts keep their original precision
- Missing values are written `NA`

### 4. Footnote
- Below the table, left-aligned, same width as the table, small grey text, wrapping
- In order: source and cutoff date → definitions of the table's metrics → disclaimer → a bold final sentence
- Mode A English template:

> Source: {source}, as of {as_of}. Performance rank based on performance within the respective index. Contribution rank (not available for NASDAQ) represents price performance multiplied by weight in index. All corporate names and market data shown above are for illustrative purposes only and are not a recommendation, offer to sell, or a solicitation of an offer to buy any security. Indexes are unmanaged, do not incur management fees, costs and expenses and cannot be invested in directly. **Past performance is no guarantee of future results.**

- For modes B and C, replace the metric definitions in the middle with this table's metrics; if there is no index row, drop the "Indexes are unmanaged…" sentence
- The Chinese version is a full translation, ending in the bold sentence 「过往业绩不代表未来表现。」

## Visual parameters (table width 720px; colours are estimates)
| Element | Value |
|---|---|
| Latin/number font | `Inter`, falling back to `Helvetica Neue`, Helvetica, Arial |
| Chinese font | `Noto Sans CJK SC` / `Source Han Sans SC`, falling back to `PingFang SC`, `Microsoft YaHei` |
| Number columns | `font-feature-settings: "tnum" 1` (tabular figures); wrap the minus sign separately in `"tnum" 0` to avoid `- 8.56` |
| Title/header background | `#ACDCEC` |
| Title/header text | `#1B2A4A`; title 15px / 700, header 13.5px / 600, line height 1.25 |
| Normal rows | `#595959`, 13.5px, line height 26px |
| Benchmark/total rows | `#2B2B2B`, 600 |
| Row divider | 1px `#D9D9D9` |
| Cell padding | 10px left, 12px right |
| Outer border | 1px `#D0D0D0` |
| Footnote | English 10px / Chinese 10.5px, `#6B6B6B`, line height 1.4, 7px above |

## Step 4: Render
1. Write the data as a spec JSON (format below)
2. Run `python3 render_table.py spec.json {output prefix}` to produce `{prefix}_en.html/.png` and `{prefix}_zh.html/.png`
3. Open both PNGs and check against the checklist; fix the spec and re-render if anything is off
4. Deliver both PNGs (and the HTML, for easy editing)

Spec format:
```json
{
  "langs": {
    "en": {"title": "...", "h1": ["", "", "1-month", "1-year", "Last"],
           "h2": ["", "YTD (%)", "return (%)", "return (%)", "price ($)"],
           "foot": "Source: ... <b>Past performance is no guarantee of future results.</b>", "foot_size": "10px"},
    "zh": {"title": "...", "h1": [...], "h2": [...], "foot": "...<b>过往业绩不代表未来表现。</b>", "foot_size": "10.5px"}
  },
  "formats": ["pct", "pct", "pct", "money"],
  "rows": [
    {"ticker": "NVDA", "name": {"en": "NVIDIA Corp", "zh": "英伟达"}, "cells": [25.7, 4.4, 24.2, 233.95]},
    {"name": {"en": "S&P 500", "zh": "标普 500"}, "cells": [12.8, null, null, null], "bench": true}
  ]
}
```
`formats`: `pct` = 1 decimal, `money` = 2 decimals with thousands separator, `raw` = output as given (use it for ranks and share counts). `null` renders as `NA`.

Optional flags: `--langs en` renders only the listed languages; `--no-png` writes HTML only and does not need Playwright.

Without `render_table.py`, hand-write a single-file HTML following the structure and visual parameters above, and screenshot the `#wrap` container with Playwright at `device_scale_factor=2`.

## Checklist
- [ ] Mode identified correctly; columns match the mode
- [ ] Both Chinese and English versions produced
- [ ] Every stock carries `(TICKER)`; benchmark/total rows do not
- [ ] All data comes from authoritative sources; no aggregator data
- [ ] All data shares one cutoff date; footnote date, source and return basis are correct
- [ ] Sorted descending by column 2; benchmark/total rows at the correct position and bold
- [ ] No header wrapping; no `%` or `$` in cells; no gap after the minus sign
- [ ] Title and header form one continuous light-blue band
- [ ] The footnote's last sentence is bold
- [ ] Do not draw the "Legend" badge from the top-left of the original screenshot (a screenshot artifact)
