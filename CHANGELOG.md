# Changelog

All notable changes. Versions follow the [releases](https://github.com/imoneys10k/schwab-table/releases) page.

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
