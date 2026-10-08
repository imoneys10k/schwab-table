# Contributing

Thanks for helping. A few ground rules keep the numbers trustworthy.

## Ground rules
- **Name every source.** Official exchange closes, index providers, filings and the user's own data come first. Yahoo and other aggregated data only when clearly labelled as aggregated, and never numbers from memory. See `SKILL.en.md`.
- **`null` is not zero.** Missing data renders as `NA`, never as 0 or a guess.
- **Change behaviour -> update the docs.** `SKILL.md` (Traditional Chinese, the file Claude loads), `SKILL.en.md`, and the READMEs and website. The READMEs (English, Traditional Chinese, Japanese, French) and `docs/index.html` are **generated**: edit `tools/docs_content.py` (text) or `tools/site_template.html` (page), then run `python3 tools/build_docs.py`. A test fails if they are out of date. `README.zh-CN.md` is a hand-written pointer.
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
4. If you changed text or examples shown in the READMEs or the website, run `python3 tools/build_docs.py` and commit the result.
