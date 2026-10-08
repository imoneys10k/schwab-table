# Schwab-style stock performance table

> English translation of [SKILL.md](SKILL.md). `SKILL.md` (Chinese) is the file Claude loads and the source of truth; if the two ever differ, `SKILL.md` wins.

## When to use
The user wants to turn a set of stocks into the kind of table found in Schwab research: a light-blue title/header band, thin grey row dividers, and a small-print disclaimer footnote. By default, output **both a Chinese and an English version**, one HTML file each, then render each to PNG with Playwright at 2x.

For a **price chart** (several symbols over a period), jump to "Chart mode" at the end.

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
- `as_of`: use the screenshot's own timestamp when it has one. If the numbers are intraday (a US-Eastern midday screenshot), say "as of {time}, prices delayed" and **do not call it a closing date**; with no timestamp, use the **most recent US market close** matching the screenshot (a Taipei/Beijing morning screenshot = the previous US Eastern trading day)
- When the total row does not match the rows (it may include holdings or cash not shown), **show the broker's figures as they are and do not correct them**; say so in the footnote or reply and tell the user the difference you computed

### Mode C (tickers only)
- Prefer `fetch_prices.py` for the official closes (faster than a browser and reproducible); `--start` must be more than a year back to get the 1-year return, e.g. `python3 fetch_prices.py NVDA AMD MU --start 2025-09-01 -o data/x.json`; then compute YTD, 1-month and 1-year returns yourself per the "Data-source rules" below. Fall back to Claude in Chrome only if that fails
- No benchmark row unless the user mentions a comparison; if they do, fetch benchmarks with `--benchmark SPY,COMP` and say that SPY is only a proxy for the S&P 500
- With more than 15 stocks, confirm with the user first whether to include them all; a table that long loses the research-note look

## Data-source rules: official sources first, explicitly labelled global data

"Authoritative" means the **original publisher** of the data, or an official body that republishes the publisher's data verbatim with attribution. Aggregator sites are not original publishers; Yahoo is the explicitly labelled exception for global daily closes.

### 1. Allowed sources

US listings retain Nasdaq; Shanghai/Shenzhen use exchange website endpoints. Other markets may use Yahoo Finance daily closes, explicitly labelled as aggregated data. Include currency, exchange-local trading dates and retrieval times; never label Yahoo prices as official exchange closes.

| Data | Allowed source | How to get it |
|---|---|---|
| The user's own data | Brokerage screenshots, exports or web pages the user provides | Use as given; do not rewrite |
| Stock closing prices | The listing exchange's official close: Nasdaq.com historical quotes (including consolidated closes for NYSE-listed stocks), NYSE.com | The page is JS-rendered, so WebFetch cannot read it; open `https://www.nasdaq.com/market-activity/stocks/{ticker}/historical` in Claude in Chrome and read the table |
| Stock closing prices (fallback) | The user's brokerage (e.g. Schwab quote/research pages; requires the user to be logged in) | Claude in Chrome |
| S&P 500 | S&P Dow Jones Indices; or FRED republishing it verbatim (series `SP500`, credited to S&P Dow Jones Indices) | WebFetch `https://fred.stlouisfed.org/series/SP500` |
| Nasdaq Composite | Nasdaq Global Indexes; or FRED (series `NASDAQCOM`) | WebFetch `https://fred.stlouisfed.org/series/NASDAQCOM` |
| Splits, official company names | Company IR announcements, SEC EDGAR filings | WebFetch / WebSearch restricted to official domains |
| Rank within an index (mode A) | Only accepted from the user (from Schwab, Bloomberg, etc.) | Never computed by Claude |

### 2. Forbidden sources
- Aggregators such as ChartRow, stockanalysis.com, Google Finance, Investing.com, MarketBeat, Seeking Alpha, Stocktwits (Google Finance was observed to return stale prices)
- Forums, blogs, auto-generated SEO pages, AI summaries
- Any number from the model's memory
- When no authoritative source can be found, **do not fall back** to the above. Instead: stop and tell the user which ticker and what is missing and ask them to supply it (e.g. a Schwab export), or fill that cell with `NA` and say so in the reply

### 3. Compute returns yourself from official closes
Ready-made "YTD %" figures on web pages mostly come from aggregators and are not used directly. Compute from the allowed sources above:
- **YTD** = close on the cutoff date ÷ close on the last trading day of the previous year − 1
- **1-month** = close on the cutoff date ÷ close on the same day one month earlier − 1 (if that day was a market holiday, use the nearest earlier trading day)
- **1-year** = same, one year earlier
- If a split or reverse split falls inside the window, adjust the older prices by the ratio in the IR announcement
- Nasdaq uses split-adjusted price returns; Yahoo uses close rather than dividend-adjusted adjclose. Shanghai/Shenzhen closes are unadjusted and corporate actions may distort returns. Verify corporate actions before describing those changes as investment returns. Cross-currency comparisons use each listing currency, without FX conversion
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
| 1 | Left | 30% | `{name} ({TICKER})`; header left blank |
| 2 | Right | 13% | Primary metric (the sort key) |
| 3–5 | Right | 19% each | Remaining metrics |

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

## Visual parameters (table width 760px; colours are estimates)
| Element | Value |
|---|---|
| Latin/number font | `Inter`, falling back to `Helvetica Neue`, Helvetica, Arial |
| Chinese font | `Noto Sans CJK TC` / `Source Han Sans TC`, falling back to `PingFang TC`, `Microsoft JhengHei` |
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

Optional flags: `--langs en` renders only the listed languages; `--no-png` writes HTML only and does not need Playwright; `--scale 3` raises the PNG resolution (default 2).

Without `render_table.py`, hand-write a single-file HTML following the structure and visual parameters above, and screenshot the `#wrap` container with Playwright at `device_scale_factor=2`.

## Checklist
- [ ] Mode identified correctly; columns match the mode
- [ ] Both Chinese and English versions produced
- [ ] Every stock carries `(TICKER)`; benchmark/total rows do not
- [ ] All data comes from allowed sources; Yahoo is labelled aggregated; no model-memory numbers
- [ ] All data shares one cutoff date; footnote date, source and return basis are correct
- [ ] Sorted descending by column 2; benchmark/total rows at the correct position and bold
- [ ] No header wrapping; no `%` or `$` in cells; no gap after the minus sign
- [ ] Title and header form one continuous light-blue band
- [ ] The footnote's last sentence is bold
- [ ] Do not draw the "Legend" badge from the top-left of the original screenshot (a screenshot artifact)

---

# Chart mode: price history for several symbols over a period

## When to use
The user wants to see how one or more symbols moved over a period, their cumulative return or drawdown (e.g. "chart NVDA and MU this year", "compare these names from March to June"). The look matches the performance tables: light-blue title band, thin grey rules, small-print footnote. Output **both a Chinese and an English version** (PNG + HTML). Up to **9 symbols**, plus an optional benchmark.

## Workflow
1. **Fix the symbols and the period.** Use the dates the user gives exactly; with none, use **year to date**. The start is indexed to 100 at the close on or before the start date (YTD = the last close of the previous year)
2. **Fetch the data** (US: Nasdaq; Shanghai/Shenzhen: official exchange website endpoints; other markets: Yahoo):
   ```bash
   python3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 --end 2026-10-02 -o data/watch.json
   ```
   - US Nasdaq daily closes are official and split-adjusted, excluding dividends, with about 10 years of history. Other markets have the source and adjustment limitations below.
   - The default benchmark is **SPY** (an S&P 500 ETF, same source; the chart and footnote say it is only a proxy for the index). `--benchmark COMP` uses the Nasdaq Composite; `--benchmark SP500` uses the S&P 500 index republished by FRED (FRED sometimes times out); `--benchmark none` draws no benchmark
   - Separate several benchmarks with commas: `--benchmark SPY,COMP`. `COMP`, `NDX` and a few more are indexes and are looked up as indexes directly (the same letters can also be a US stock ticker, e.g. COMP is Compass Inc); when a code is ambiguous use `index:COMP`, `etf:SPY` or `stock:XXX` to force the class
   - **Global symbols:** `7203.T`, `0700.HK`, `SAP.DE`, `600519.SS`, `000001.SZ`. Numeric codes require an explicit exchange suffix. Beijing is not supported by the official adapter; use a user CSV. Use `--benchmark none` unless a benchmark was requested.
   - Exchange A-share closes are unadjusted; Shenzhen history is limited. Missing base prices cause an error, never a silently shortened return period. Yahoo is aggregated; coverage varies. Unfinished current-day bars are excluded.
   - **Total return:** Nasdaq's dividend data is not split-adjusted and ETFs have none, so total returns cannot be computed automatically. When the user supplies a CSV with an `Adj Close` column, use `csv_to_prices.py --adj-close` and the chart is labelled total return. Price-return and total-return series cannot share a chart
   - Responses are cached for 12 hours (`--refresh` bypasses it). If the network fails, the last cache is used with a warning, and the footnote's retrieval date is when that cache was actually fetched
   - Use only the configured sources, never other aggregators or numbers from the model's memory. If the script exits with code 2, or `errors` in the JSON is non-empty, some symbol was not fetched: **stop and tell the user which one**; do not fill the gap
   - Claude supplies the company names (English full name + common Chinese name) in the spec's `names`
3. **Write the spec** (format below) and run:
   ```bash
   python3 render_chart.py spec.json out/watch
   ```
   This produces `out/watch_en.html/.png` and `out/watch_zh.html/.png`
4. Open both PNGs and check them against the checklist; fix the spec and re-render if needed. Deliver both PNGs (and the HTML)

## Layouts
| `layout` | Content | Use for |
|---|---|---|
| `auto` (default) | `lines` for up to 5 symbols, `multiples` for 6–9 | the usual case |
| `lines` | line chart + drawdown panel + summary table | 2–5 symbols |
| `multiples` | one small chart per symbol, **the same y-scale in every panel**, a drawdown strip under each, grey dashed benchmark | 6–9 symbols |

- `y_scale`: `auto` (default), `linear`, `log`. `auto` switches to a **log scale** when the highest and lowest index levels differ by more than 3x, and the subtitle says "Log scale"
- `drawdown`: draw drawdowns (default on); `table`: summary table in the `lines` layout (default on)

## Specification
- The y-axis is always an index with the start = 100, and **a chart has one y-axis, never two**
- **Colours are fixed per symbol, in a fixed order, and never follow the ranking**: blue `#2a78d6`, orange `#eb6834`, green `#1baf7a`, yellow `#eda100`, pink `#e87ba4` (checked for colour-blind separability). The benchmark is always a dark-grey dashed line `#595959`. In the small multiples every stock is navy `#1B2A4A` and the benchmark a light-grey dashed line
- Line width 2px (benchmark 1.6px dashed); a dot with a 2px white ring at each line end, **with the symbol and return labelled directly at the line end**, nudged apart with small leader lines when they collide. Green and yellow have low contrast on white, so the direct labels and the summary table are not optional
- Summary table columns: period return, annualized volatility, max drawdown, last price; sorted by return descending, benchmark row bold, benchmark last price `NA`
- Annualized volatility = standard deviation of daily price returns × √252; drawdown = the close's decline from the highest close up to that day within the period; max drawdown = the lowest drawdown in the period
- Footnote, in order: source and cutoff date, retrieval date, start, metric definitions, the proxy note (when an ETF is the benchmark), disclaimer, bold last sentence
- The span of the period sets the x-axis ticks: weekly within 45 days, monthly up to about a year, quarterly or yearly beyond

## Spec format
```json
{
  "data": "data/watch.json",
  "symbols": ["NVDA", "MU"],
  "names": {"NVDA": {"en": "NVIDIA Corp", "zh": "英伟达"}, "MU": {"en": "Micron Technology Inc", "zh": "美光科技"}},
  "benchmark_name": {"en": "S&P 500 (SPY)", "zh": "标普 500 (SPY)"},
  "benchmarks": ["SPY", "COMP"], "colors": {"NVDA": "#2a78d6"},
  "layout": "auto", "y_scale": "auto", "drawdown": true, "table": true,
  "start": "2026-01-01", "end": "2026-10-02",
  "title": {"en": "...", "zh": "..."}, "note": {"en": "...", "zh": "..."}
}
```
Everything except `data` is optional. Without `start` / `end` the data file's range is used; `note` is put at the start of the footnote (the examples use it to say "Hypothetical example"). `benchmarks` selects and orders the benchmarks in the data file; `benchmark_name` can be `{"en": ..., "zh": ...}` (for the first benchmark) or given per symbol; `colors` overrides individual line colours with `#rrggbb` (the default palette is checked for colour-blind separability, so check contrast yourself if you change it). Command-line options: `--langs en` renders one language, `--no-png` writes HTML only, `--pdf` also saves a vector PDF, `--scale 3` raises the PNG resolution (default 2), `--theme dark` renders a dark theme (tables and charts). In the HTML files, hovering over a chart shows every line's value for that day.

## Checklist (charts)
- [ ] At most 9 symbols; the period matches the request (year to date if none was given)
- [ ] Data comes from allowed endpoints; Yahoo, currency, last trading dates and warnings are labelled; missing symbols were reported
- [ ] Both language versions produced; source, cutoff date and start in the footnote are correct
- [ ] One y-axis only; colours fixed per symbol; line-end labels present, not overlapping, not clipped
- [ ] When an ETF is the benchmark the footnote says it is a proxy; when a log scale is used the subtitle says so
- [ ] Summary table sorted by return descending, benchmark row bold, numbers consistent with the line-end labels
- [ ] A-share unadjusted-price risks and local currencies are disclosed; Yahoo is not called official; total-return charts use user-supplied dividend-adjusted closes


## Institutional templates and Traditional Chinese

Chinese output defaults to Traditional Chinese, including charts; `zh` input keys remain compatible. When the user requests Morgan, Blackstone or IBKR, read [references/institutional-tables.md](references/institutional-tables.md) and prepare the appropriate column schema. Schwab remains the default. Do not infer account weights or holdings from daily prices.
