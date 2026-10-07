"""Fetch daily closes from Nasdaq, Shanghai/Shenzhen exchanges and Yahoo Finance (standard library only).

Usage:
  python3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 --end 2026-10-02 -o data/watch.json
  python3 fetch_prices.py NVDA --benchmark SPY,COMP     # several benchmarks (SPY = S&P 500 ETF, COMP = Nasdaq Composite index)
  python3 fetch_prices.py index:COMP etf:SPY             # a prefix (stock: etf: index:) forces the asset class
  python3 fetch_prices.py NVDA --benchmark SP500        # S&P 500 index via FRED (best effort)
  python3 fetch_prices.py NVDA --refresh                # ignore the local cache
  python3 fetch_prices.py 7203.T 0700.HK SAP.DE 600519.SS 000001.SZ --benchmark none -o data/global.json

Notes
- Source: https://api.nasdaq.com (the data behind nasdaq.com historical quotes). Closes are split-adjusted and
  exclude dividends, i.e. price returns. About 10 years of daily history are available. US-listed symbols only;
  other markets use Yahoo Finance's public chart endpoint, explicitly labelled as aggregated data.
- Shanghai (.SS) and Shenzhen (.SZ) use official exchange website endpoints, without automatic fallback to Yahoo.
  These closes are unadjusted; corporate actions can distort returns. Shenzhen's history window is limited.
  Use explicit exchange suffixes (7203.T, 0700.HK, SAP.DE); bare numeric codes are ambiguous.
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
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

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


def http_get(url, accept="application/json", timeout=40, tries=3, headers=None):
    last = None
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept, **(headers or {})})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e
            time.sleep(1.5 * (n + 1))
    raise FetchError(f"request failed after {tries} tries: {last}")


def get_json(url, tries=3, headers=None):
    last = None
    for n in range(tries):
        try:
            response = json.loads(http_get(url, tries=1, headers=headers))
            if not isinstance(response, dict):
                raise FetchError("expected a JSON object")
            return response
        except (FetchError, json.JSONDecodeError) as e:
            last = str(e)
            if n + 1 < tries:
                time.sleep(2 * (n + 1))
    raise FetchError(f"no usable JSON response after {tries} tries: {last}")


def parse_close(s):
    return float(re.sub(r"[$,]", "", s))


def parse_date(s):
    return dt.datetime.strptime(s, "%m/%d/%Y").date()


# ---- cache ---------------------------------------------------------------------
def cache_path(sym, start):
    return CACHE_DIR / f"v2_{re.sub(r'[^A-Za-z0-9_-]', '_', sym)}_{start.isoformat()}.json"


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


def clean_points(rows):
    """Validate daily prices before they enter return calculations."""
    points = {}
    try:
        for day, close in rows:
            close = float(close)
            if not math.isfinite(close) or close <= 0:
                raise ValueError(f"invalid close on {day}: {close}")
            if day in points and points[day] != close:
                raise ValueError(f"conflicting closes on {day}")
            points[day] = close
    except (TypeError, ValueError) as e:
        raise FetchError(f"invalid historical prices: {e}") from e
    if not points:
        raise LookupError("no daily closes returned")
    return sorted(points.items())


def exchange_series(sym):
    code, market = sym.rsplit(".", 1)
    if not re.fullmatch(r"\d{6}", code):
        raise LookupError(f"{sym}: use a six-digit code with .SS or .SZ")
    if market == "SS":
        url = f"https://yunhq.sse.com.cn:32042/v1/sh1/dayk/{code}?select=date,open,high,low,close,volume&begin=0&end=-1"
        raw = get_json(url, headers={"Referer": "https://www.sse.com.cn/"})
        if str(raw.get("code")) != code:
            raise LookupError(f"{sym}: Shanghai exchange returned no matching symbol")
        rows = raw.get("kline") or []
        source, exchange = "Shanghai Stock Exchange (official website, unadjusted closes)", "XSHG"
        prices = [(dt.datetime.strptime(str(r[0]), "%Y%m%d").date(), r[4]) for r in rows]
    else:
        url = f"https://www.szse.cn/api/market/ssjjhq/getHistoryData?cycleType=32&marketId=1&code={code}"
        raw = get_json(url, headers={"Referer": "https://www.szse.cn/"})
        data = raw.get("data") or {}
        if str(raw.get("code")) != "0" or data.get("code") != code:
            raise LookupError(f"{sym}: Shenzhen exchange returned no matching symbol")
        source, exchange = "Shenzhen Stock Exchange (official website, unadjusted closes)", "XSHE"
        prices = [(dt.date.fromisoformat(r[0]), r[2]) for r in data.get("picupdata", [])]
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))
    # Exchange website day bars may include an unfinished session.
    prices = [(day, close) for day, close in prices if day < now.date() or now.hour >= 15]
    return {"class": "stocks", "source": source, "source_url": url, "currency": "CNY", "exchange": exchange,
            "timezone": "Asia/Shanghai", "adjustment": "unadjusted", "basis": "price", "points": clean_points(prices)}


def yahoo_series(sym, start, today, forced=None):
    first = int(dt.datetime.combine(start, dt.time(), dt.timezone.utc).timestamp())
    last = int(dt.datetime.combine(today + dt.timedelta(days=1), dt.time(), dt.timezone.utc).timestamp())
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?period1={first}&period2={last}&interval=1d"
    chart = get_json(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://finance.yahoo.com/"}).get("chart") or {}
    if chart.get("error") or not chart.get("result"):
        raise LookupError(f"{sym}: no data from Yahoo Finance: {chart.get('error')}")
    data = chart["result"][0]
    meta = data.get("meta") or {}
    stamps = data.get("timestamp") or []
    quotes = data.get("indicators", {}).get("quote") or []
    closes = quotes[0].get("close", []) if quotes else []
    if len(stamps) != len(closes):
        raise FetchError(f"{sym}: Yahoo returned mismatched timestamps and closes")
    zone_name = meta.get("exchangeTimezoneName") or "UTC"
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError:
        zone = dt.timezone(dt.timedelta(seconds=meta.get("gmtoffset", 0)))
    regular = meta.get("currentTradingPeriod", {}).get("regular") or {}
    session_end = regular.get("end")
    session_date = dt.datetime.fromtimestamp(session_end, zone).date() if session_end else None
    prices = []
    for stamp, close in zip(stamps, closes):
        if close is None:
            continue
        day = dt.datetime.fromtimestamp(stamp, zone).date()
        if session_end and day == session_date and time.time() < session_end:
            continue  # do not present a live partial day bar as a closing price
        prices.append((day, close))
    cls = forced or {"ETF": "etf", "INDEX": "index"}.get(meta.get("instrumentType"), "stocks")
    return {"class": cls, "source": "Yahoo Finance (aggregated daily closes)", "source_url": url,
            "currency": meta.get("currency") or "", "exchange": meta.get("exchangeName") or "",
            "timezone": zone_name, "adjustment": "provider_close", "basis": "price", "points": clean_points(prices)}


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
            entry = {"class": cls, "source": source, "points": pts, "currency": "", "basis": "price"}
        elif sym.endswith((".SS", ".SZ")):
            entry = exchange_series(sym)
        elif re.fullmatch(r"\d{4,6}", sym):
            raise LookupError(f"{sym}: ambiguous numeric code; include an exchange suffix, e.g. 600519.SS, 000001.SZ, 7203.T")
        elif sym.endswith(".BJ"):
            raise LookupError(f"{sym}: Beijing exchange is not supported by the official A-share adapter; use csv_to_prices.py")
        elif "." in sym or sym.startswith("^"):
            entry = yahoo_series(sym, fetch_from, today, forced)
        else:
            cls, pts = nasdaq_series(sym, fetch_from, today, forced)
            source = NASDAQ_SOURCE
            entry = {"class": cls, "source": source, "points": pts, "currency": "" if cls == "index" else "USD",
                     "timezone": "America/New_York", "adjustment": "split", "basis": "price"}
    except FetchError as e:
        if cached:
            when = dt.datetime.fromtimestamp(cached["saved_at"]).strftime("%Y-%m-%d %H:%M")
            return cached, f"{sym}: {e}; using cached data from {when}"
        raise
    entry = dict(entry)
    entry["points"] = [[d.isoformat(), c] for d, c in entry["points"]]
    entry["fetched_at"] = dt.datetime.now().astimezone().isoformat(timespec="seconds")
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
            bases = [d for d, _ in pts if d <= start]
            if not bases or (start - bases[-1]).days > 14:
                raise LookupError(f"{sym}: source history starts at {entry['points'][0][0]}; no close within 14 days before {start}. Use a later --start or csv_to_prices.py")
            out["series"][sym] = {k: v for k, v in entry.items() if k not in ("points", "saved_at")}
            out["series"][sym].update(benchmark=is_bench, points=[[d.isoformat(), c] for d, c in pts], last_close_date=pts[-1][0].isoformat())
            if entry.get("adjustment") == "unadjusted":
                warn = f"{sym}: exchange closes are unadjusted; splits and other corporate actions may distort returns and drawdowns"
                out["warnings"].append(warn)
                print(f"warning: {warn}", file=sys.stderr)
            stamps.append(entry.get("fetched_at") or dt.datetime.now().astimezone().isoformat(timespec="seconds"))
            print(f"{sym:8s} {entry['class']:6s} {len(pts):4d} closes  {pts[0][0]} .. {pts[-1][0]}")
        except (LookupError, FetchError, ValueError, TypeError, KeyError, IndexError) as e:
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
