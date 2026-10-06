# Evals

Two kinds of checks live here, both written for [skill-creator](https://github.com/anthropics/skills)-style runs.

| File | What it checks |
|---|---|
| `evals.json` | Six realistic requests (watchlist table, holdings screenshot, line chart, nine-symbol log chart, Hong Kong stocks, total return) with expected behaviour and checkable assertions |
| `trigger_eval.json` | 20 queries (10 should trigger the skill, 10 near-misses should not) for tuning the `description` |
| `holdings_screenshot.png` | Fictional brokerage screenshot used by eval 2 (`make_holdings_screenshot.py` regenerates it) |

## Running
- **Functional evals:** for each entry, run your agent once with the skill and once without, give it the `prompt` (and the input file), then check the `assertions` against what it produced. Ground truth for the numbers comes from `fetch_prices.py` (official Nasdaq closes).
- **Trigger evals:** skill-creator's `run_eval.py` / `run_loop.py` take `trigger_eval.json` directly. They call `claude -p`, so run them in a normal terminal where that command is logged in. They did not work inside a managed desktop session (401), so the description in `SKILL.md` has **not** been validated by this set yet.

## Results so far
See [RESULTS.md](RESULTS.md).
