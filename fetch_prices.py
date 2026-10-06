"""Fetch daily closing prices from Nasdaq's official historical-quote API (stdlib only).

Usage:
  python3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 --end 2026-10-02 -o data/watch.json
  python3 fetch_prices.py NVDA --benchmark COMP        # Nasdaq Composite index
  python3 fetch_prices.py NVDA --benchmark SP500       # S&P 500 index via FRED (best effort)

Notes
- Source: https://api.nasdaq.com (the data behind nasdaq.com historical quotes). Closes are split-adjusted
  and exclude dividends, i.e. price returns. About 10 years of daily history are available.
- Symbols are looked up as stock, then ETF, then index. Missing/unknown symbols are reported, never guessed.
- The default benchmark is SPY (an S&P 500 ETF, official Nasdaq close) because FRED is not always reachable.
"""
import argparse
import csv
import datetime as dt
import io
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
API = "https://api.nasdaq.com/api/quote/{sym}/historical?assetclass={cls}&fromdate={f}&todate={t}&limit=9999"
FRED = {"SP500": "S&P 500 (S&P Dow Jones Indices, via FRED)", "NASDAQCOM": "Nasdaq Composite (Nasdaq Global Indexes, via FRED)"}


def http_get(url, accept="application/json", timeout=40, tries=3):
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            time.sleep(1.5 * (n + 1))
    raise RuntimeError(f"request failed after {tries} tries: {last}")


def parse_close(s):
    return float(re.sub(r"[$,]", "", s))


def parse_date(s):
    return dt.datetime.strptime(s, "%m/%d/%Y").date()


def nasdaq_series(sym, start, today):
    """Return (asset_class, [(date, close)]) ascending, or raise LookupError."""
    for cls in ("stocks", "etf", "index"):
        # The API only answers reliably when todate is recent, so ask up to today and trim locally.
        url = API.format(sym=urllib.parse.quote(sym), cls=cls, f=start.isoformat(), t=today.isoformat())
        d = json.loads(http_get(url))
        if d.get("data") and d["data"]["tradesTable"].get("rows"):
            rows = d["data"]["tradesTable"]["rows"]
            pts = sorted((parse_date(r["date"]), parse_close(r["close"])) for r in rows if r.get("close") not in (None, "", "N/A"))
            return cls, pts
        time.sleep(0.4)
    raise LookupError(f"{sym}: no data from Nasdaq (unknown symbol, or no trading history in the range)")


def fred_series(sid, start):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}&cosd={start.isoformat()}"
    rows = list(csv.reader(io.StringIO(http_get(url, accept="text/csv", timeout=45, tries=2))))[1:]
    pts = [(dt.date.fromisoformat(r[0]), float(r[1])) for r in rows if len(r) > 1 and r[1] not in ("", ".")]
    if not pts:
        raise LookupError(f"{sid}: FRED returned no data")
    return "fred", pts


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbols", nargs="+", help="tickers, e.g. NVDA MU AAPL")
    ap.add_argument("--start", help="period start YYYY-MM-DD (default: Jan 1 of the end year = YTD)")
    ap.add_argument("--end", help="period end YYYY-MM-DD (default: latest close)")
    ap.add_argument("--benchmark", default="SPY", help="SPY (default), COMP, NDX, SP500 (FRED), NASDAQCOM (FRED), or none")
    ap.add_argument("-o", "--out", required=True, help="output JSON path")
    a = ap.parse_args()

    today = dt.date.today()
    end = dt.date.fromisoformat(a.end) if a.end else today
    start = dt.date.fromisoformat(a.start) if a.start else dt.date(end.year, 1, 1)
    if start >= end:
        sys.exit("error: --start must be before --end")
    if (today - start).days > 3650:
        print("warning: Nasdaq provides about 10 years of daily history; earlier dates will be missing", file=sys.stderr)
    fetch_from = start - dt.timedelta(days=14)  # leaves room for the close on or before the start date

    syms = [s.upper() for s in a.symbols]
    bench = None if a.benchmark.lower() == "none" else a.benchmark.upper()
    out = {"fetched_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "start": start.isoformat(), "end": end.isoformat(),
           "benchmark": bench, "series": {}, "errors": []}
    todo = [(s, False) for s in syms] + ([(bench, True)] if bench else [])
    for sym, is_bench in todo:
        try:
            if sym in FRED:
                cls, pts = fred_series(sym, fetch_from)
                source = FRED[sym]
            else:
                cls, pts = nasdaq_series(sym, fetch_from, today)
                source = "Nasdaq (official closing prices, split-adjusted)"
            pts = [(d, c) for d, c in pts if fetch_from <= d <= end]
            if not pts:
                raise LookupError(f"{sym}: no closes between {fetch_from} and {end}")
            out["series"][sym] = {"class": cls, "benchmark": is_bench, "source": source,
                                  "points": [[d.isoformat(), c] for d, c in pts]}
            print(f"{sym:8s} {cls:6s} {len(pts):4d} closes  {pts[0][0]} .. {pts[-1][0]}")
        except (LookupError, RuntimeError, json.JSONDecodeError) as e:
            out["errors"].append(str(e))
            print(f"error: {e}", file=sys.stderr)
        time.sleep(0.5)

    import os
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {a.out}")
    if out["errors"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
