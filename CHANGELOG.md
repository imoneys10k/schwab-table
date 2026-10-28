# Changelog

All notable changes. Versions follow the [releases](https://github.com/imoneys10k/schwab-table/releases) page.




## 0.8.2 (2026-10-28)

### Added
- **Animated WebP.** `render_motion.py --formats webp` (or `gif,webp`) writes `OUT_PREFIX_{lang}.webp`, with the GIF's size and timing but in full colour without dithering and about a third smaller (example line chart 1.1 MB against 1.6 MB, ETF holdings 310 KB against 450 KB). Many ffmpeg builds lack the WebP encoder, so ffmpeg hands the frames over as an APNG and Pillow encodes them one at a time (quality 80, no forced key frames, so each frame stores only what changed). It is not in the default set because WeChat and Xiaohongshu may not play it, and it needs Pillow (`python3 -m pip install pillow`).

### Changed
- **The GIF no longer fades back by default.** The loop fade made GIFs about a fifth larger; it now applies to the MP4 only (0.4 s), and the GIF and WebP cut straight back to the first frame. A `--loop-fade` value given still applies to every format. The four gallery GIFs went from 4.3 MB to 3.1 MB together (example line chart 2.0 MB to 1.6 MB).

## 0.8.1 (2026-10-28)

### Added
- **`--canvas` for social formats.** `render_motion.py --canvas 3:4` (also `4:5`, `9:16`, `1:1`, `16:9`) centres the animation on a canvas of that aspect ratio, filled with the page colour, so Xiaohongshu, Instagram, Douyin or Reels do not crop it. The GIF, the MP4 and both halves of the Live Photo get the same canvas.
- **Live Photo key-photo marker.** The `.mov` now carries the timed-metadata track `com.apple.quicktime.still-image-time` that iPhone videos have, pointing at the last frame (the key photo). It is laid out as AVFoundation's `AVAssetWriter` writes it; AVFoundation reads it back as `-1` at the key-photo time, and macOS Photos (`PHLivePhoto`) still accepts the pair. Live Photos are now about 3.2 s at 30 fps.
- **The chart's summary table re-sorts as the lines draw.** Rows slide into the order of the return so far; a row passes another only when it leads by 6 % of the current spread (at least 2 points), so close lines do not make the table flicker. It is back in its static order at the end.
- **Loop fade.** The GIF and MP4 end with a 0.4 s cross-fade back to their first frame, so the loop restarts without a jump (`--loop-fade`, 0 for a hard cut). The fade and the moving table make the example line-chart GIF about 2 MB instead of 1.3 MB; `--gif-width 600` brings it to about 1.5 MB, and `--loop-fade 0` with it to about 1.2 MB.

### Changed
- **Table timing follows the row count.** Without `--draw`, rows come in over 2 to 6 s depending on how many there are (about 2.2 s for 6 rows, 4.4 s for 16), and each row takes about 0.7 s.
- **About twice as fast.** All languages are captured at once in one browser, the three formats share one set of screenshots (the Live Photo reuses the loop's frames), and the ffmpeg encodes run side by side. A chart in both languages and all three formats takes about 30 s instead of about 65 s.
- **`--fps` is documented as the MP4 frame rate.** `--fps 60` is smoother and takes about twice the time and size. GIFs stay at 25 fps at most (GIF frame times are whole hundredths of a second, so 30 fps cannot be shown evenly) and Live Photos at 30.

## 0.8.0 (2026-10-28)

### Added
- **Animated charts.** `render_motion.py` takes a `render_chart.py` spec and writes the chart as a looping GIF, an H.264 MP4 and an Apple Live Photo (`_live.jpg` + `_live.mov`). The lines draw from left to right with a glowing head, the line-end labels ride along with live values, the current date sits above the cursor, and the summary table (return, volatility, max drawdown, last price) is recomputed as of the cursor; the drawdown panel and the small multiples animate the same way. It then fades into the static chart: the last frame is pixel-identical to the `render_chart.py` PNG. Light and dark themes, English and Traditional Chinese, `--draw`, `--hold`, `--fps`, `--scale`, `--gif-width`.
  - Live Photo pairing is written in plain Python, so it works on macOS, Linux and Windows without exiftool or PyObjC: an Apple MakerNote (tag 17, the content identifier) in the JPEG, laid out exactly as macOS ImageIO writes it, and a QuickTime `moov/meta` `mdta` key `com.apple.quicktime.content.identifier` in the MOV. Both were read back with ImageIO and AVFoundation, and macOS Photos (`PHLivePhoto`) accepts the pair as a Live Photo while rejecting the same pair with mismatched identifiers.
- **Animated tables and ETF holdings.** `render_motion.py` also takes a `render_table.py` spec (all four templates: Schwab, Morgan, Blackstone, IBKR) or `fetch_holdings.py` output, recognised by its content. Table rows fade in from top to bottom and every number with a decimal point counts up from 0 in its own format (Blackstone's `(5.2)%` included), while ranks, share counts and text simply appear. Holdings bars grow one after another from rank 1, swap parts included, with the weight counting up and the cumulative column adding up the weights shown so far. `--style` and the holdings options (`--top`, `--mode`, `--by`, `--merge-classes`, `--names`) work as in the static renderers. The last frame is pixel-identical to the static PNG; checked for every table template, light and dark, and the holdings modes, in both languages. GIFs keep a narrow layout's own width instead of being stretched to 760 px.
  - Needs ffmpeg; the installers print a hint when it is missing and every other feature works without it.
  - Tests (`tests/test_motion.py`, offline): the EXIF / MakerNote bytes, the MOV atoms, the frame timeline, and the path and row order the frame script depends on, input detection, the number pattern the row script counts up, and the holdings and table markup it relies on. Four animated examples in the gallery.

## 0.7.0 (2026-10-12)

### Added
- **ETF top holdings.** `fetch_holdings.py` reads an ETF's holdings from the issuer's own published file and `render_holdings.py` draws the top N (13 by default) as bars plus a table, with weight, cumulative weight, sector, the total of the rest and a footnote that states source, as-of date and rules. English and Traditional Chinese, PNG + HTML, light and dark themes, optional PDF.
  - Issuers: State Street SPDR (SPY, XLK, ...), iShares (15 funds with verified product ids, e.g. IVV), Vanguard equity ETFs (VOO, ...), NEOS (QQQI), Roundhill (NCLD, DRAM, ...), Tema (DISK). Invesco (QQQ, QQQM, ...) and Destiny (DXYZ) are deliberately **not** fetched: their terms of use forbid automated access, so the tool stops with an import command instead (a browser-based Invesco adapter was written and removed). Any other fund: `--csv` with a file you download. Each endpoint used was checked against the host's robots.txt; terms of use were read for Invesco, Destiny and SSGA only.
  - Swap-aware ranking for funds such as NCLD and DRAM: swaps are added to the shares of the same stock (matched by CUSIP/SEDOL); cash, money-market funds, T-bills and options are listed on a separate line and not ranked. `--mode lines` ranks every line as listed. `--merge-classes` adds share classes together.
  - Weights are shown as the issuer reports them (no extra decimals), missing weights stay NA, and a warning is printed when the holdings date is more than 10 days old (Vanguard publishes monthly; on 2026-10-12 its newest file was dated 2026-08-31, and its `asOfType` and date parameters return nothing newer). A holdings date more than 10 days before retrieval is also shown in the chart subtitle, e.g. "Holdings as of 2026-08-31 (42 days old)".
  - As-of dates are the **pricing day**. NEOS and Roundhill stamp each file with the next trading day, but the prices inside are the previous close (checked against official closes: Roundhill's 10-09 file holds the 10-09 closes and is stamped 10-12). Charts used to show the stamp; they now show the pricing day and the footnote says what the issuer stamped. The live check compares each file's own prices with Nasdaq's official closes, so a changed convention fails the weekly run.
  - Holdings cache is 1 hour (was planned as 6) and the script says when it served the cache and how old it was; `--refresh` downloads again. Banner, social card, README taglines and the website now mention ETF holdings.
  - `render_holdings.py --by sector|name` for funds with thousands of lines (AGG has 13,418, so its top 13 single bonds are 5%): groups are added together and ranked, with the line count shown. A footnote now says when single lines tell little about concentration (100 or more lines and a top-N under 15%). iShares bond lines carry coupon and maturity so they can be told apart.
  - Swap weights were checked against Roundhill's own site script: it adds a swap's weight to the stock's weight (NCLD by CUSIP, DRAM by the first four letters of the name), drops cash and Treasury bills, and shows holdings dated one day before the file's stamp. Roundhill funds now also add a company's other listings (DRAM: SKHY into SK hynix, 005935 KS into Samsung: 22.41% and 25.01%). A swap's notional basis is still the issuer's and is not independently verified. The footnote no longer says every issuer's own view does this; Tema, for one, lists lines without adding them.
  - `tools/live_check.py` and the weekly `live-check` workflow fetch one real fund per issuer (SPY, IVV, TLT, VOO, QQQI, DRAM, DISK) and check holdings count, weight total, as-of age, swap rows and rendering, so a changed issuer page is noticed early. Offline tests prove each failure mode is caught.
  - Tests (`tests/test_holdings.py`, offline), fictional examples (`examples/etf_holdings_*`), SKILL.md / SKILL.en.md sections, README and website entries, an installer smoke test, and a live two-issuer check in CI.

### Changed
- Docs no longer present the project as Claude-only: the banner, social card and website tag read "AI agent skills", the badge is "Agent Skills", and the intro, flow chart and install notes say the skills are built for Claude Code and usable from Codex and other coding agents.

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
