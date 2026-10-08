# Results

## 2026-10-07: functional evals, one run per request, with the skill vs. without

| | With skill | Without skill |
|---|---|---|
| Assertions passed | 100% | 42% |
| Time per run (mean) | 82 s | 93 s |
| Tokens per run (mean) | 71k | 74k |

**Read this with care.** The assertions encode this project's rules (official data only, the Schwab table style, no invented numbers), which an agent without the skill has no way to know. The comparison shows the skill delivers what it promises; it is not a neutral quality contest. Six requests and one run each also say nothing about variance.

What the runs showed:
- **Numbers:** in the three runs whose numbers can be checked against official closes (the watchlist table, the line chart, the nine-symbol chart), every with-skill number matched the ground truth. The holdings table (eval 2) was checked against the screenshot instead: every value was reproduced as shown.
- **Honesty:** for Hong Kong stocks and for total return the skill-guided agent stopped and asked for a CSV instead of drawing a chart. Without the skill, the agent built both charts from Yahoo Finance and labelled the source. By this project's rule that fails; for a user who just wants a picture it is arguably more useful.
- **Style:** without the skill, outputs were reasonable but never the Schwab research look.
- **Gaps found, now fixed in `SKILL.md`:** mode C still told the agent to use a browser although `fetch_prices.py` exists; no rule for screenshots stamped with an intraday time; no rule for totals that do not add up; benchmark rows were added unasked.
- **Not tested:** whether the skill is triggered at the right moments (see `README.md`), and a comparison of colours against Schwab's original chart (the original image was not available).
