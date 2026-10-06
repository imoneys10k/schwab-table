"""Turn your own price CSV files into the JSON that render_chart.py reads (standard library only).

Use this for markets Nasdaq's API does not cover (Hong Kong, A-shares, ...), for data exported from your broker,
or for total-return charts built from adjusted closes.

Usage:
  python3 csv_to_prices.py 0700.HK=tencent.csv 600519=moutai.csv --benchmark HSI=hsi.csv -o data/hk.json
  python3 csv_to_prices.py NVDA=nvda.csv --benchmark SPY=spy.csv --adj-close -o data/total.json

Each CSV needs a header row with a date column (Date, Trade Date, 日期, ...) and a close column
(Close, Close/Last, 收盘价, ...). With --adj-close the "Adj Close" column is used instead and the chart is
labelled as total return (only use it when that column includes dividends, e.g. Yahoo-style exports).
Dates may be YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD or MM/DD/YYYY. Numbers may carry $ or thousands separators.
You are responsible for the data: the source is recorded as "User-provided data (<file name>)".
"""
import argparse
import csv
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

DATE_COLS = ("date", "trade date", "trading date", "日期", "交易日期", "time")
CLOSE_COLS = ("close", "close/last", "closing price", "close price", "收盘价", "收盘", "price")
ADJ_COLS = ("adj close", "adj. close", "adjusted close", "adj_close", "复权收盘价")


def parse_date(s):
    s = s.strip().strip('"')
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d", "%m/%d/%Y"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"unrecognised date {s!r} (use YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD or MM/DD/YYYY)")


def parse_number(s):
    return float(re.sub(r"[$¥€£,\s]", "", s.strip().strip('"')))


def find_col(header, names):
    low = [h.strip().lower().lstrip("﻿") for h in header]
    for n in names:
        if n in low:
            return low.index(n)
    return None


def read_csv(path, adj=False):
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if len(rows) < 3:
        raise ValueError(f"{path}: needs a header row and at least two data rows")
    header = rows[0]
    di = find_col(header, DATE_COLS)
    ci = find_col(header, ADJ_COLS if adj else CLOSE_COLS)
    if di is None:
        raise ValueError(f"{path}: no date column found in header {header}")
    if ci is None:
        raise ValueError(f"{path}: no {'adjusted close' if adj else 'close'} column found in header {header}")
    pts = {}
    for n, r in enumerate(rows[1:], start=2):
        if not r or all(not x.strip() for x in r):
            continue
        try:
            pts[parse_date(r[di])] = parse_number(r[ci])
        except (ValueError, IndexError) as e:
            raise ValueError(f"{path} line {n}: {e}")
    return sorted(pts.items())


def build(pairs, benches, adj, start=None, end=None):
    series = {}
    for sym, path in pairs + benches:
        pts = read_csv(path, adj)
        series[sym] = {"class": "csv", "benchmark": (sym, path) in benches, "basis": "total" if adj else "price",
                       "source": f"User-provided data ({Path(path).name})", "points": [[d.isoformat(), c] for d, c in pts]}
    last = max(dt.date.fromisoformat(v["points"][-1][0]) for v in series.values())
    end = end or last
    start = start or dt.date(end.year, 1, 1)
    return {"fetched_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "start": start.isoformat(), "end": end.isoformat(),
            "benchmark": benches[0][0] if benches else None, "benchmarks": [b for b, _ in benches], "series": series, "errors": [], "warnings": []}


def split_pair(s):
    if "=" not in s:
        sys.exit(f"error: expected SYMBOL=file.csv, got {s!r}")
    sym, path = s.split("=", 1)
    return sym.strip().upper(), path.strip()


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pairs", nargs="+", help="SYMBOL=file.csv")
    ap.add_argument("--benchmark", action="append", default=[], help="SYMBOL=file.csv (repeat for several benchmarks)")
    ap.add_argument("--adj-close", action="store_true", help="use the Adj Close column and label the chart as total return")
    ap.add_argument("--start", help="period start YYYY-MM-DD (default: Jan 1 of the end year)")
    ap.add_argument("--end", help="period end YYYY-MM-DD (default: latest date in the files)")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    try:
        out = build([split_pair(p) for p in a.pairs], [split_pair(p) for p in a.benchmark], a.adj_close,
                    dt.date.fromisoformat(a.start) if a.start else None, dt.date.fromisoformat(a.end) if a.end else None)
    except (ValueError, OSError) as e:
        sys.exit(f"error: {e}")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    for sym, v in out["series"].items():
        print(f"{sym:8s} csv    {len(v['points']):4d} closes  {v['points'][0][0]} .. {v['points'][-1][0]}")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
