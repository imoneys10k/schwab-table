# Changelog

All notable changes. Versions follow the [releases](https://github.com/imoneys10k/schwab-table/releases) page.



## 0.6.2 (2026-10-08)

### Changed
- README (English, Traditional Chinese, Japanese, French) rewritten around what the project is now: two skills, four table styles, price charts with market routing, quarterly earnings review, data and honesty rules, complete file list, tests and evals. The v0.5 / v0.6 sections that had been appended below the license are folded into the page, and the gallery and flow chart cover every feature.
- Website rebuilt from the same content: highlights, a ten-image gallery, a quarterly-earnings section linking the demo, a data-sources table, install tabs and prompt in four languages.
- Banner and social card mention quarterly earnings and Traditional Chinese.
- CONTRIBUTING: sources must be named (Yahoo only when labelled aggregated) instead of the older "authoritative data only".

### Added
- `tools/build_docs.py`, `tools/docs_content.py`, `tools/site_template.html`: one content table generates the four READMEs and the website. `tests/test_docs.py` fails if they are out of date, if a link, image or anchor is dead, or if a language is missing text.

### Fixed
- The `--ref` row of the install options table had lost a full stop ("pin a version Run the installer ...").

## 0.6.1 (2026-10-08)

### Fixed
- `BRK.B`, `BF.B` and other US share-class tickers: dotted symbols were all sent to Yahoo, which spells them `BRK-B` and returned 404. One-letter class suffixes now go to Nasdaq (which serves them); exchange suffixes (`.HK`, `.T`, `.SS`, ...) still use their own adapters.
- Re-running `install.sh` / `install.ps1` without `--ref` after pinning with `--ref` reported "Already up to date" and stayed on the old tag. It now moves back to `main`.
- `--uninstall` only checked that `SKILL.md` existed. It now requires the folder to be this skill (`name: schwab-performance-table`).
- A price cache saved before the day's close was published could be reused for up to 12 hours and miss that close. A cache is now reused only if it already has the newest expected close (US market clock, no tz database needed).
- `INDEX_SYMBOLS` no longer lists `SPX`, `RUT` and `DJIA` (the API returns "Symbol not exists" for them).
- More than two benchmarks were drawn with identical styling; the chart now keeps the first two and warns.

### Changed
- Docs: the mode C `--start` example no longer hard-codes a date; `evals/RESULTS.md` no longer claims more than was checked.
- Removed an unused parameter in the hover code and the theme identity check in the CSS (`ptitle` is now a theme key).

### Tests
- `tests/test_fetch_reliability.py` (symbol routing, retries, cache freshness around DST, benchmark limit); CI also checks that a pinned install can be updated and that a foreign folder is not uninstalled.

## 0.6.0 (2026-10-08)

### Added
- HSBC-style quarterly earnings review Skill: ticker + fiscal period to bilingual PNG/HTML, single-quarter values, YoY/QoQ comparisons, source-backed commentary and inspectable facts/audit ledgers.
- Official Apple financial PDFs and SEC US-GAAP Company Facts adapters, with retrieval timestamps and 12-hour caches. Verified official report imports support other markets.
- Reproducible AAPL FY2025Q3 / FY2025Q4 examples and an online quarter/language comparison page; Q4 distinguishes GAAP comparisons from the prior-year one-time tax adjustment.
- Installers register the earnings Skill beside the existing Skill, share dependencies and smoke-test HSBC output. Existing unmanaged skills are preserved.
- Tests for fiscal periods, cumulative cash-flow arithmetic, source evidence, PDF columns, missing data and installed Skill execution.

### Validation and limits
- 60 local tests pass; both Apple quarters were verified against official PDFs. SEC live access returned 403 in the development environment; its parser is covered by fixed known-answer tests. Global quarterly filings are not claimed as automatically covered.

## 0.5.0 (2026-10-08)

### Added
- Morgan-style two-period return/risk matrix, Blackstone-style two-period grouped performance and IBKR-style holdings/exposure templates, calibrated against specific public report samples.
- `--style` / `spec.style` and explicit column schemas, with unchanged supplied values, NA for missing data and preserved institutional grouping.
- `prices_to_table.py`: daily closes to matrix/grouped report specs, sharing existing return, volatility and drawdown calculations; actual common close and base-price audit data.
- Source Sans 3 and Droid Sans with licence notices; source-font substitutions are documented.
- Free global daily-price routing: US Nasdaq, mainland China exchange websites, other exchange-suffixed listings / indexes via clearly labelled Yahoo aggregation.

### Changed
- All Chinese tables, charts, examples, Skill instructions and site copy use Traditional Chinese. Existing `zh` keys and filenames remain compatible; Chinese README moves to `README.zh-Hant.md` with an old-link redirect.
- Install smoke tests cover all four table styles. New styles use white paper; existing Schwab / chart dark themes remain available.

## 0.4.0 (2026-10-07)

### Added
- `csv_to_prices.py`: turn your own CSV files (broker exports, Hong Kong / A-share prices, adjusted closes) into chart data; `--adj-close` makes a total-return chart.
- `fetch_prices.py`: 12-hour local cache, fallback to the last cache when the network fails (with a warning), several benchmarks (`--benchmark SPY,COMP`), `index:` / `etf:` / `stock:` prefixes, clear message for non-US symbols.
- Charts: dark theme (`--theme dark`, tables too), vector PDF (`--pdf`), several benchmarks, custom line colours, hover tooltips in the HTML.
- Installers: `--ref` / `-Ref` to pin a version, `--uninstall` / `-Uninstall`.
- Unit tests (`tests/`), a `tests` workflow (3 operating systems, Python 3.9 and 3.13, example regeneration check, a live Nasdaq smoke test), issue and pull request templates, Dependabot for Actions.

- `evals/`: six realistic test requests with assertions, a 20-query trigger set, and the results of the first eval run (see `evals/RESULTS.md`).

### Fixed
- `COMP` (and `NDX`, ...) was looked up as a stock ticker (COMP is also Compass Inc), giving wrong numbers for the Nasdaq Composite. Known index codes now go straight to the index.

### Changed
- `SKILL.md` after the first eval run: mode C prefers `fetch_prices.py`; screenshots with an intraday timestamp are not called a closing date; totals that do not add up are shown as the broker shows them and reported; no benchmark row unless asked. The `description` is more explicit about when to trigger (not yet validated, see `evals/README.md`).
- Footnotes list only the sources of the symbols actually drawn.
- Shared rendering code moved to `render_common.py`.

## 0.3.0
- Price charts (`fetch_prices.py`, `render_chart.py`): lines and small-multiples layouts, drawdown, log scale, up to 9 symbols, any period.
- Bundled Inter font; `--scale` option; restyled README and a GitHub Pages site.

## 0.2.0
- One-click installers for macOS, Linux and Windows; install prompt for AI agents; CI on three operating systems.

## 0.1.1 / 0.1.0
- Schwab-style performance tables (ranking, holdings, watchlist); four-language README; MIT license.
