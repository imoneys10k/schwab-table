# Contributing

Thanks for helping. A few ground rules keep the numbers trustworthy.

## Ground rules
- **Authoritative data only.** Official exchange closes, index providers, filings, or the user's own data. No aggregator numbers, and nothing from memory. See `SKILL.en.md`.
- **`null` is not zero.** Missing data renders as `NA`, never as 0 or a guess.
- **Change behaviour -> update the docs.** `SKILL.md` (Chinese, the file Claude loads), `SKILL.en.md`, and the four READMEs.
- **Examples use fictional companies and synthetic data**, so no real market data is redistributed.

## Setup
```bash
git clone https://github.com/imoneys10k/schwab-table.git && cd schwab-table
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt && playwright install chromium
python3 -m unittest discover -s tests -v      # no browser needed
```

## Before opening a pull request
1. `python3 -m unittest discover -s tests` passes.
2. If output changed, regenerate the examples:
   ```bash
   python3 examples/make_sample_prices.py
   for m in neural9 holdings watchlist; do python3 render_table.py examples/${m}_spec.json examples/$m; done
   for m in chart_lines chart_multiples; do python3 render_chart.py examples/${m}_spec.json examples/$m; done
   ```
   CI regenerates the HTML and fails if it differs from what is committed.
3. For a new calculation, add a known-answer test in `tests/test_calc.py`.
