**English** · [简体中文](README.zh-CN.md) · [日本語](README.ja.md) · [Français](README.fr.md)

# schwab-table

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![install-test](https://github.com/imoneys10k/schwab-table/actions/workflows/install-test.yml/badge.svg)](https://github.com/imoneys10k/schwab-table/actions/workflows/install-test.yml)

A Claude Skill that turns a stock list, a brokerage holdings screenshot, or ready-made return/rank data into a Charles Schwab research-style performance table, rendered in both Chinese and English (PNG + HTML).

![English](examples/neural9_en.png)

![Chinese](examples/neural9_zh.png)

## Three modes

| Mode | Input | Columns 2–5 | Example |
|---|---|---|---|
| A. Ranking table | Each stock's YTD return and its rank within the S&P 500 / NASDAQ | YTD, S&P 500 performance rank, S&P 500 contribution rank, NASDAQ performance rank | [EN](examples/neural9_en.png) · [中文](examples/neural9_zh.png) |
| B. Holdings table | A brokerage holdings screenshot or export | Open P/L %, today's P/L, average cost, shares | [EN](examples/holdings_en.png) · [中文](examples/holdings_zh.png) |
| C. Watchlist table | Tickers only | YTD, 1-month, 1-year, latest close | [EN](examples/watchlist_en.png) · [中文](examples/watchlist_zh.png) |

Mode A uses data from a public Charles Schwab chart. The mode B and C examples use fictional companies and made-up numbers, for illustration only.

## Using it with Claude

Once installed, just ask in plain language, for example:

- Make a performance table for NVDA, AMD and MU.
- Turn this holdings screenshot into a Schwab-style table. (attach the screenshot)
- Make a 2026 Neural9 ranking table from this data.

## Data sources

Authoritative data only: official exchange closing prices, index providers (S&P Dow Jones Indices, Nasdaq Global Indexes, optionally via FRED), company IR / SEC filings, or the user's own brokerage data. Returns are computed from official closing prices; ready-made percentages from aggregator sites are not used. See [SKILL.md](SKILL.md) for the rules (in Chinese; an English translation is in [SKILL.en.md](SKILL.en.md)).

## Files

- `SKILL.md`: the skill definition Claude loads (structure, visual parameters, data-source rules, checklist), in Chinese
- `SKILL.en.md`: English translation of `SKILL.md`, for human readers
- `install.sh` / `install.ps1`: one-click installers for macOS / Linux and Windows
- `render_table.py`: the renderer. Reads a JSON spec and writes Chinese and English HTML plus 2x PNG
- `requirements.txt`: Python dependency (Playwright)
- `examples/`: one spec plus rendered output for each of the three modes
- `assets/`: social preview image

## Install

Works on macOS, Linux and Windows. You need Python 3.9+ (to render tables); git is optional.

### Let your AI agent install it

Paste this to Claude Code, Codex or any other coding agent:

```text
Install the skill from https://github.com/imoneys10k/schwab-table for me.
Detect my operating system. On macOS or Linux, run:
  curl -fsSL https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.sh | sh
On Windows, in PowerShell, run:
  irm https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.ps1 | iex
If I use an agent other than Claude, install into that agent's skills folder instead
(macOS/Linux: add `--dir <path>` after `sh -s --`; Windows: save install.ps1 and run it with -Dir <path>).
When it finishes, confirm that "Render OK" was printed, then tell me to restart so the skill loads.
```

### Or run it yourself

macOS / Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.sh | sh
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.ps1 | iex
```

The installer puts the skill in `~/.claude/skills/schwab-performance-table` (`%USERPROFILE%\.claude\skills\...` on Windows), creates a private Python virtual environment inside it, installs Playwright and Chromium (about 100 MB), and renders the example table as a smoke test. It prints `Render OK` when everything works. Restart Claude afterwards so the skill is picked up. To read the script before running it, open [install.sh](install.sh) or [install.ps1](install.ps1).

| Option (macOS / Linux) | Option (Windows) | Effect |
|---|---|---|
| `--dir PATH` | `-Dir PATH` | Install somewhere else (for example another agent's skills folder). `CLAUDE_SKILLS_DIR` changes the default root. |
| `--skip-deps` | `-SkipDeps` | Skip Python / Playwright / Chromium (only fetch the files) |

When piping, pass options with `sh -s --`, for example `curl -fsSL .../install.sh | sh -s -- --dir ~/my-skills/schwab`. On Windows, save `install.ps1` and run `.\install.ps1 -Dir C:\path`.

**Update:** run the same command again. **Uninstall:** delete the install folder.

**Troubleshooting:** on Debian/Ubuntu install `python3-venv` first; on Linux, if Chromium fails to start, run `sudo <install folder>/.venv/bin/python -m playwright install-deps chromium`.

## Manual rendering

If you used the installer, `render_table.py` automatically switches to its virtual environment, so plain `python3 render_table.py ...` works. Otherwise, Python 3.9+ is required:

```bash
pip install -r requirements.txt && playwright install chromium
python3 render_table.py examples/neural9_spec.json out/neural9
```

Options: `--langs en` renders only the listed languages (comma-separated); `--no-png` writes HTML only and does not need Playwright. Missing output folders are created automatically.

Fonts: Inter for Latin text and numbers, Noto Sans CJK SC / Source Han Sans SC for Chinese. Falls back to Helvetica Neue / PingFang when they are not installed.

## Disclaimer

This project only generates table styling and does not provide investment advice. The data in the examples is for illustration only.

## License

[MIT](LICENSE)
