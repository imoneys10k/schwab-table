"""Generate examples/sample_prices.json: SYNTHETIC prices for fictional companies (same schema as fetch_prices.py).

Not real market data. Run from anywhere: python3 examples/make_sample_prices.py
"""
import datetime as dt
import json
import math
import random
from pathlib import Path

START, BASE, END = dt.date(2025, 12, 18), dt.date(2025, 12, 31), dt.date(2026, 10, 2)
# symbol, daily vol, YTD target %, price at the base date
FICTIONAL = [
    ("ACRB", 0.022, 88.4, 103.0), ("STRK", 0.017, 41.7, 220.9), ("HOOL", 0.015, 22.3, 104.3),
    ("GLBX", 0.012, 6.8, 57.1), ("INSY", 0.016, -5.2, 42.1), ("UMBB", 0.021, -18.6, 1516.0),
    ("WAYN", 0.030, 241.0, 31.5), ("CYDN", 0.014, 14.5, 88.0), ("SOYL", 0.011, -9.8, 24.6),
]
BENCH = ("BNCH", 0.007, 12.8, 5000.0)


# US market holidays inside the sample window (NYSE calendar)
HOLIDAYS = {dt.date(2025, 12, 25), dt.date(2026, 1, 1), dt.date(2026, 1, 19), dt.date(2026, 2, 16), dt.date(2026, 4, 3),
            dt.date(2026, 5, 25), dt.date(2026, 6, 19), dt.date(2026, 7, 3), dt.date(2026, 9, 7)}


def bdays(a, b):
    d, out = a, []
    while d <= b:
        if d.weekday() < 5 and d not in HOLIDAYS:
            out.append(d)
        d += dt.timedelta(days=1)
    return out


def make(seed, vol, target, p_base, dates):
    rnd = random.Random(seed)
    w, x = [], 0.0
    for _ in dates:
        x += rnd.gauss(0, vol)
        w.append(x)
    b, n = dates.index(BASE), len(dates)
    tgt = math.log(1 + target / 100)
    adj = [w[i] - ((i - b) / (n - 1 - b)) * (w[-1] - w[b] - tgt) if i >= b else w[i] for i in range(n)]
    return [round(p_base * math.exp(a - adj[b]), 2) for a in adj]


def main():
    dates = bdays(START, END)
    series = {}
    for i, (sym, vol, tgt, p) in enumerate(FICTIONAL + [BENCH]):
        is_b = sym == BENCH[0]
        px = make(100 + i * 7, vol, tgt, p, dates)
        series[sym] = {"class": "index" if is_b else "stocks", "benchmark": is_b,
                       "source": "Synthetic sample data (not real market data)",
                       "points": [[d.isoformat(), c] for d, c in zip(dates, px)]}
    out = {"fetched_at": "2026-10-05T00:00:00+00:00", "start": "2026-01-01", "end": END.isoformat(),
           "benchmark": BENCH[0], "series": series, "errors": []}
    path = Path(__file__).resolve().parent / "sample_prices.json"
    path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
