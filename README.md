**English** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Français](README.fr.md)

# schwab-table

A Claude Skill that turns a stock list, a brokerage holdings screenshot, or ready-made return/rank data into a Charles Schwab research-style performance table, rendered in both Chinese and English (PNG + HTML).

![Example](examples/neural9_en.png)

## Three modes

| Mode | Input | Columns 2–5 |
|---|---|---|
| A. Ranking table | Each stock's YTD return and its rank within the S&P 500 / NASDAQ | YTD, S&P 500 performance rank, S&P 500 contribution rank, NASDAQ performance rank |
| B. Holdings table | A brokerage holdings screenshot or export | Open P/L %, today's P/L, average cost, shares |
| C. Watchlist table | Tickers only | YTD, 1-month, 1-year, latest close |

## Data sources

Authoritative data only: official exchange closing prices, index providers (S&P Dow Jones Indices, Nasdaq Global Indexes, optionally via FRED), company IR / SEC filings, or the user's own brokerage data. Returns are computed from official closing prices; ready-made percentages from aggregator sites are not used. See [SKILL.md](SKILL.md) for details.

## Files

- `SKILL.md`: the skill definition (structure, visual parameters, data-source rules, checklist)
- `render_table.py`: the renderer. Reads a JSON spec and writes Chinese and English HTML plus 2x PNG
- `examples/`: a Mode A example (data from a public Charles Schwab chart, as of 10/2/2026)

## Install

Put this folder into Claude's skills directory, or upload it under Skills in claude.ai settings.

## Manual rendering

```bash
pip install playwright && playwright install chromium
python3 render_table.py examples/neural9_spec.json out/neural9
```

Fonts: Inter for Latin text and numbers, Noto Sans CJK SC / Source Han Sans SC for Chinese. Falls back to Helvetica Neue / PingFang when they are not installed.

## Disclaimer

This project only generates table styling and does not provide investment advice. The data in the examples is for illustration only.
