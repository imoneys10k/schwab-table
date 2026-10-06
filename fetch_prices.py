"""Fetch daily closing prices from Nasdaq's official historical-quote API (standard library only).

Usage:
  python3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 --end 2026-10-02 -o data/watch.json
  python3 fetch_prices.py NVDA --benchmark SPY,COMP     # several benchmarks (SPY = S&P 500 ETF, COMP = Nasdaq Composite index)
  python3 fetch_prices.py index:COMP etf:SPY             # a prefix (stock: etf: index:) forces the asset class
  python3 fetch_prices.py NVDA --benchmark SP500        # S&P 500 index via FRED (best effort)
  python3 fetch_prices.py NVDA --refresh                # ignore the local cache

Notes
- Source: https://api.nasdaq.com (the data behind nasdaq.com historical quotes). Closes are split-adjusted and
  exclude dividends, i.e. price returns. About 10 years of daily history are available. US-listed symbols only;
  for Hong Kong / A-shares / anything else, export a CSV and use csv_to_prices.py.
- Symbols are looked up as stock, then ETF, then index (COMP, NDX and a few other index codes go straight to index, because
  the same letters are also stock tickers). Missing or unknown symbols are reported, never guessed.
- Responses are cached for 12 hours (~/.cache/schwab-table). If the network fails and an older cache exists, it is
  used with a warning, and the output's retrieval date shows when that data was actually fetched.
- The default benchmark is SPY (an S&P 500 ETF, official Nasdaq close) because FRED is not always reachable.
"""
import argparse
import csv
import datetime as dt
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
API = "https://api.nasdaq.com/api/quote/{sym}/historical?assetclass={cls}&fromdate={f}&todate={t}&limit=9999"
FRED = {"SP500": "S&P 500 (S&P Dow Jones Indices, via FRED)", "NASDAQCOM": "Nasdaq Composite (Nasdaq Global Indexes, via FRED)"}
NASDAQ_SOURCE = "Nasdaq (official closing prices, split-adjusted)"
CACHE_DIR = Path(os.environ.get("SCHWAB_TABLE_CACHE", Path.home() / ".cache" / "schwab-table"))
CACHE_TTL = 12 * 3600
NON_US = re.compile(r"(\.[A-Z]{1,3}$)|(^\d{4,6}$)")
# These are indexes, but the same letters are also US stock tickers (COMP = Compass Inc), so they must not be looked up as stocks.
INDEX_SYMBOLS = {"COMP", "NDX", "NQUS500LC", "SPX", "DJIA", "RUT"}
CLASSES = {"stock": "stocks", "stocks": "stocks", "etf": "etf", "index": "index"}


class FetchError(Exception):
    pass


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
    raise FetchError(f"request failed after {tries} tries: {last}")


def get_json(url, tries=3):
    last = None
    for n in range(tries):
        text = http_get(url, tries=1)
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            last = text[:80].replace("\n", " ")
            time.sleep(2 * (n + 1))  # an HTML page here usually means rate limiting
    raise FetchError(f"unexpected non-JSON response (rate limited?): {last!r}")


def parse_close(s):
    return float(re.sub(r"[$,]", "", s))


def parse_date(s):
    return dt.datetime.strptime(s, "%m/%d/%Y").date()


# ---- cache ---------------------------------------------------------------------
def cache_path(sym, start):
    return CACHE_DIR / f"{re.sub(r'[^A-Za-z0-9_-]', '_', sym)}_{start.isoformat()}.json"


def cache_read(sym, start):
    p = cache_path(sym, start)
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d, time.time() - d["saved_at"]
    except (OSError, ValueError, KeyError):
        return None, None


def cache_write(sym, start, entry):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path(sym, start).write_text(json.dumps(dict(entry, saved_at=time.time())), encoding="utf-8")
    except OSError:
        pass  # a read-only home directory must not break fetching


# ---- sources ---------------------------------------------------------------------
def split_symbol(spec):
    """'etf:SPY' -> ('SPY', 'etf'); 'COMP' -> ('COMP', None). The prefix forces the Nasdaq asset class."""
    if ":" in spec:
        cls, sym = spec.split(":", 1)
        if cls.lower() not in CLASSES:
            raise LookupError(f"{spec}: unknown prefix {cls!r} (use stock:, etf: or index:)")
        return sym.upper(), CLASSES[cls.lower()]
    return spec.upper(), None


def nasdaq_series(sym, start, today, forced=None):
    """Return (asset_class, [(date, close)]) ascending, or raise LookupError / FetchError."""
    if NON_US.search(sym):
        raise LookupError(f"{sym}: Nasdaq's API covers US-listed symbols only. For Hong Kong, A-shares or other markets, "
                          "export a CSV from your broker or the exchange and use csv_to_prices.py")
    for cls in ([forced] if forced else ["index"] if sym in INDEX_SYMBOLS else ["stocks", "etf", "index"]):
        # The API only answers reliably when todate is recent, so ask up to today and trim locally.
        url = API.format(sym=urllib.parse.quote(sym), cls=cls, f=start.isoformat(), t=today.isoformat())
        d = get_json(url)
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


def get_series(spec_sym, fetch_from, today, refresh=False):
    """Return (entry, warning). entry = {class, source, points, fetched_at} with points as [[iso, close], ...]."""
    sym, forced = split_symbol(spec_sym)
    cached, age = cache_read(f"{forced}_{sym}" if forced else sym, fetch_from)
    if cached and not refresh and age < CACHE_TTL:
        return cached, None
    try:
        if sym in FRED:
            cls, pts = fred_series(sym, fetch_from)
            source = FRED[sym]
        else:
            cls, pts = nasdaq_series(sym, fetch_from, today, forced)
            source = NASDAQ_SOURCE
    except FetchError as e:
        if cached:
            when = dt.datetime.fromtimestamp(cached["saved_at"]).strftime("%Y-%m-%d %H:%M")
            return cached, f"{sym}: {e}; using cached data from {when}"
        raise
    entry = {"class": cls, "source": source, "points": [[d.isoformat(), c] for d, c in pts],
             "fetched_at": dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    cache_write(f"{forced}_{sym}" if forced else sym, fetch_from, entry)
    return entry, None


def build(symbols, bench, start, end, today, refresh=False):
    fetch_from = start - dt.timedelta(days=14)  # leaves room for the close on or before the start date
    out = {"fetched_at": None, "start": start.isoformat(), "end": end.isoformat(), "benchmark": bench[0] if bench else None,
           "benchmarks": bench, "series": {}, "errors": [], "warnings": []}
    todo = [(s, False) for s in symbols] + [(b, True) for b in bench if b not in symbols]
    bench = [split_symbol(b)[0] for b in bench]
    out["benchmark"] = bench[0] if bench else None
    out["benchmarks"] = bench
    stamps = []
    for spec_sym, is_bench in todo:
        try:
            sym = split_symbol(spec_sym)[0]
            entry, warn = get_series(spec_sym, fetch_from, today, refresh)
            if warn:
                out["warnings"].append(warn)
                print(f"warning: {warn}", file=sys.stderr)
            pts = [(dt.date.fromisoformat(d), c) for d, c in entry["points"] if fetch_from <= dt.date.fromisoformat(d) <= end]
            if not pts:
                raise LookupError(f"{sym}: no closes between {fetch_from} and {end}")
            out["series"][sym] = {"class": entry["class"], "benchmark": is_bench, "source": entry["source"],
                                  "points": [[d.isoformat(), c] for d, c in pts]}
            stamps.append(entry.get("fetched_at") or dt.datetime.now().astimezone().isoformat(timespec="seconds"))
            print(f"{sym:8s} {entry['class']:6s} {len(pts):4d} closes  {pts[0][0]} .. {pts[-1][0]}")
        except (LookupError, FetchError) as e:
            out["errors"].append(str(e))
            print(f"error: {e}", file=sys.stderr)
        time.sleep(0.3)
    out["fetched_at"] = min(stamps) if stamps else dt.datetime.now().astimezone().isoformat(timespec="seconds")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbols", nargs="+", help="tickers, e.g. NVDA MU AAPL")
    ap.add_argument("--start", help="period start YYYY-MM-DD (default: Jan 1 of the end year = YTD)")
    ap.add_argument("--end", help="period end YYYY-MM-DD (default: latest close)")
    ap.add_argument("--benchmark", default="SPY", help="comma-separated: SPY (default), COMP, NDX, SP500 (FRED), NASDAQCOM (FRED), or none")
    ap.add_argument("--refresh", action="store_true", help="ignore the local cache")
    ap.add_argument("-o", "--out", required=True, help="output JSON path")
    a = ap.parse_args()

    today = dt.date.today()
    end = dt.date.fromisoformat(a.end) if a.end else today
    start = dt.date.fromisoformat(a.start) if a.start else dt.date(end.year, 1, 1)
    if start >= end:
        sys.exit("error: --start must be before --end")
    if (today - start).days > 3650:
        print("warning: Nasdaq provides about 10 years of daily history; earlier dates will be missing", file=sys.stderr)
    syms = [s if ":" in s else s.upper() for s in a.symbols]
    bench = [] if a.benchmark.lower() == "none" else [b.strip() if ":" in b else b.strip().upper() for b in a.benchmark.split(",") if b.strip()]
    out = build(syms, bench, start, end, today, a.refresh)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"wrote {a.out}")
    if out["errors"]:
        sys.exit(2)


if __name__ == "__main__":
    main()
