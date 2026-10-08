# Institutional report templates / 機構報表版式

`render_table.py --style schwab|morgan|blackstone|ibkr`. Omit the flag to use
`spec.style`, or Schwab for an existing five-column spec. All Chinese output is
Traditional Chinese (`zh-Hant`); the existing `zh` spec key and `_zh` filenames
remain compatible. Charts also default to Traditional Chinese text.

Institutional templates use white paper. Existing Schwab tables and charts keep
their light/dark themes. These are independent report templates, not reports
issued by or affiliated with the named institutions.

| Template | Purpose | Input |
| --- | --- | --- |
| Schwab | Ranking, watchlist, existing P/L table | Existing five-column spec |
| Morgan | Two-period return/risk matrix | Explicit columns + two column groups |
| Blackstone | Grouped performance | Name + exactly two numeric periods |
| IBKR | Detailed holdings and optional exposure | Explicit brokerage fields |

## Generate from daily closing prices

```bash
python3 fetch_prices.py AAPL MSFT NVDA --start 2024-01-01 --benchmark none -o data/prices.json
python3 prices_to_table.py data/prices.json data/matrix.json --style morgan
python3 render_table.py data/matrix.json out/matrix
python3 prices_to_table.py data/prices.json data/grouped.json --style blackstone
python3 render_table.py data/grouped.json out/grouped
```

The converter uses YTD and trailing-year periods, the chart's existing return,
sample volatility and drawdown calculations, a shared actual close date, and
the reported sources / retrieval dates. It retains base prices and observation
counts in `spec.calculation`. Missing history is an error for returns; inadequate
daily observations are NA for risk metrics. Price-return and total-return inputs
cannot be mixed. Benchmarks require `--include-benchmarks` explicitly.

Use `--names names.json` to supply verified display names and industry groups:

```json
{"AAPL":{"name":{"en":"Apple Inc","zh":"蘋果"},"group":{"en":"TECHNOLOGY","zh":"科技"}}}
```

Company names are supplied, not inferred from prices. Without that map the
symbol is the name. Do not claim Yahoo aggregate prices are exchange-published
official closes; retain unadjusted A-share and ETF-proxy warnings.

## Explicit columns and values

For the three institutional templates, columns define labels, widths, formats
and row keys. Values are supplied once; presentation never recalculates them.

```json
{
  "style":"blackstone",
  "langs":{
    "en":{"title":"Investment Performance","subtitle":"Price returns","foot":"Source and as-of date..."},
    "zh":{"title":"投資業績","subtitle":"價格回報","foot":"資料來源與截止日……"}
  },
  "columns":[
    {"key":"name","label":"","width":52},
    {"key":"qtd","label":{"en":"Quarter","zh":"本季"},"format":"pct","width":24},
    {"key":"ltm","label":{"en":"LTM","zh":"近十二月"},"format":"pct","width":24}
  ],
  "rows":[
    {"ticker":"AAPL","name":{"en":"Apple Inc","zh":"蘋果"},"group":{"en":"TECHNOLOGY","zh":"科技"},"values":{"qtd":12.3,"ltm":-4.5}}
  ]
}
```

The numeric JSON above is illustrative, not actual Apple market data. Formats:
`text`, `pct` (one decimal), `money` (two decimals / thousands separator), `raw`.
Missing is `null` -> `NA`, never zero. Specify units in column labels or footnotes.
Blackstone includes `%` in the body and uses `(4.5)%` for negative percentages.
Institutional rows retain supplied order, with consecutive `group` labels as
sections. Do not invent group aggregates or ranks. `bench:true` emphasizes a row.

Morgan additionally requires two `column_groups`, in the same order as numeric
columns. Its typical seven columns are security + 2 × return / volatility /
drawdown. `level:0|1|2` preserves the original indentation hierarchy. These are
observed historical metrics, not the original CMA's forecast assumptions.

For IBKR use `ticker`, `name`, `sector`, and explicit values such as `long`,
`short`, `net`, `long_weight`, `short_weight`, `net_weight`. Full example:
[ibkr_spec.json](../examples/ibkr_spec.json). Portfolio weights need a documented
denominator and complete account data; a partial screenshot is not a complete
account total. Do not label ordinary position weights as parsed / look-through
exposure. Optional `exposure` blocks contain their own columns and supplied rows.

Full samples: [Morgan](../examples/morgan_spec.json),
[Blackstone](../examples/blackstone_spec.json), [IBKR](../examples/ibkr_spec.json).

## Visual calibration and fonts

Source samples: [Morgan CMA, p20](https://www.morganstanley.com/assets/pdfs/2d9493c3-822f-4f18-8c28-ba3ad25e8473.pdf#page=20),
[Blackstone 3Q25, p8](https://s23.q4cdn.com/714267708/files/doc_financials/2025/q3/Blackstone3Q25EarningsPressRelease.pdf#page=8),
[IBKR Detailed TWR, p7](https://www.ibkrguides.com/reportingreference/detailed-pdf-report-twr.pdf#page=7).

Grouping, two-tier headers, indentation, grey/blue rules, serif headings and
accounting negatives are calibrated to those exact tables. Rows flow naturally
for new data; these are not fixed PDF-coordinate copies.

Inter, Source Sans 3 and Droid Sans are bundled with their source licences.
Morgan prefers an installed MSGloriolaIIStd and otherwise uses Source Sans 3;
its proprietary PDF font subsets are not bundled. Blackstone uses installed
Georgia / Trebuchet MS with serif / Source Sans fallbacks. This means some glyphs
differ from the source, especially on Linux. Traditional Chinese uses Noto Sans
CJK TC / Source Han Sans TC / PingFang TC / Microsoft JhengHei; on a minimal Linux
system install `fonts-noto-cjk`. Output embeds the bundled Latin font so HTML
does not depend on relative font paths.

## 中文使用

預設同時輸出英文及繁體中文。中文的輸入鍵仍為 `zh`；簡體輸入也會在顯示時
轉為繁體，股票代碼、數字及來源網址不變。只要使用者說「用黑石版做分組業績表」
或「用摩根士丹利版比較回報、波動和回撤」，就選擇相應模板、準備其必要字段。
IBKR 版需要真實持倉資料，不能從行情自動推算持股量或帳戶權重。
