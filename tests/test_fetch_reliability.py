"""Regression tests for symbol routing, retries, cache freshness and benchmark limits. Standard library only."""
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fetch_prices as fp  # noqa: E402
import render_chart as rc  # noqa: E402

D = dt.date
UTC = dt.timezone.utc


class Patch:
    """Temporarily replace module attributes."""

    def __init__(self, module, **attrs):
        self.module, self.attrs, self.saved = module, attrs, {}

    def __enter__(self):
        for k, v in self.attrs.items():
            self.saved[k] = getattr(self.module, k)
            setattr(self.module, k, v)

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            setattr(self.module, k, v)


class SymbolRouting(unittest.TestCase):
    def test_share_classes_are_us_tickers(self):
        for s in ("BRK.B", "BRK.A", "BF.B", "LEN.B"):
            self.assertTrue(fp.is_us_share_class(s), s)
            self.assertFalse(fp.is_non_us(s), s)

    def test_exchange_suffixes_are_not_share_classes(self):
        for s in ("7203.T", "VOD.L", "0700.HK", "SAP.DE", "600519.SS", "000001.SZ", "BRK-B"):
            self.assertFalse(fp.is_us_share_class(s), s)
        for s in ("7203.T", "0700.HK", "SAP.DE", "600519.SS", "600519"):
            self.assertTrue(fp.is_non_us(s), s)

    def test_each_symbol_reaches_the_right_adapter(self):
        calls = []
        pts = [(D(2026, 10, 2), 1.0)]

        def nas(sym, start, today, forced=None):
            calls.append(("nasdaq", sym))
            return "stocks", list(pts)

        def yah(sym, start, today, forced=None):
            calls.append(("yahoo", sym))
            return {"class": "stocks", "source": "Y", "points": list(pts)}

        def exc(sym):
            calls.append(("exchange", sym))
            return {"class": "stocks", "source": "E", "points": list(pts)}

        with tempfile.TemporaryDirectory() as tmp, Patch(fp, CACHE_DIR=Path(tmp), nasdaq_series=nas, yahoo_series=yah, exchange_series=exc):
            for sym in ("BRK.B", "AAPL", "7203.T", "0700.HK", "600519.SS", "^N225"):
                fp.get_series(sym, D(2025, 12, 18), D(2026, 10, 7), refresh=True)
        self.assertEqual(calls, [("nasdaq", "BRK.B"), ("nasdaq", "AAPL"), ("yahoo", "7203.T"), ("yahoo", "0700.HK"),
                                 ("exchange", "600519.SS"), ("yahoo", "^N225")])

    def test_index_codes_are_only_the_confirmed_ones(self):
        self.assertEqual(fp.INDEX_SYMBOLS, {"COMP", "NDX", "NQUS500LC"})   # SPX, RUT, DJIA return "Symbol not exists"


class Retries(unittest.TestCase):
    def test_get_json_retries_network_errors_then_succeeds(self):
        attempts = []

        def flaky(url, accept="application/json", timeout=40, tries=3, headers=None):
            attempts.append(1)
            if len(attempts) < 3:
                raise fp.FetchError("connection reset")
            return '{"ok": 1}'

        with Patch(fp, http_get=flaky), Patch(fp.time, sleep=lambda s: None):
            self.assertEqual(fp.get_json("http://x"), {"ok": 1})
        self.assertEqual(len(attempts), 3)

    def test_get_json_gives_up_after_the_last_try(self):
        def down(*a, **k):
            raise fp.FetchError("offline")

        with Patch(fp, http_get=down), Patch(fp.time, sleep=lambda s: None):
            with self.assertRaises(fp.FetchError):
                fp.get_json("http://x", tries=2)


class CacheFreshness(unittest.TestCase):
    def test_expected_close_date_follows_the_market_clock(self):
        cases = [
            (dt.datetime(2026, 10, 5, 14, 0, tzinfo=UTC), D(2026, 10, 2)),     # Mon 10:00 EDT: Friday's close is the newest
            (dt.datetime(2026, 10, 5, 20, 29, tzinfo=UTC), D(2026, 10, 2)),    # Mon 16:29 EDT
            (dt.datetime(2026, 10, 5, 20, 30, tzinfo=UTC), D(2026, 10, 5)),    # Mon 16:30 EDT: Monday's close
            (dt.datetime(2026, 10, 6, 10, 0, tzinfo=UTC), D(2026, 10, 5)),     # Tue 06:00 EDT
            (dt.datetime(2026, 10, 10, 15, 0, tzinfo=UTC), D(2026, 10, 9)),    # Saturday
            (dt.datetime(2026, 10, 11, 15, 0, tzinfo=UTC), D(2026, 10, 9)),    # Sunday
            (dt.datetime(2026, 1, 5, 21, 29, tzinfo=UTC), D(2026, 1, 2)),      # Mon 16:29 EST (winter)
            (dt.datetime(2026, 1, 5, 21, 30, tzinfo=UTC), D(2026, 1, 5)),      # Mon 16:30 EST
            (dt.datetime(2026, 3, 6, 21, 30, tzinfo=UTC), D(2026, 3, 6)),      # Fri 16:30 EST, the day before DST starts
            (dt.datetime(2026, 3, 9, 20, 30, tzinfo=UTC), D(2026, 3, 9)),      # Mon 16:30 EDT, after DST started
            (dt.datetime(2026, 11, 2, 20, 30, tzinfo=UTC), D(2026, 10, 30)),   # Mon 15:30 EST, after DST ended
            (dt.datetime(2026, 11, 2, 21, 30, tzinfo=UTC), D(2026, 11, 2)),    # Mon 16:30 EST
        ]
        for now, want in cases:
            self.assertEqual(fp.expected_close_date(now), want, now)

    def test_cache_is_reused_only_while_it_has_the_latest_close(self):
        calls = []

        def nas(sym, start, today, forced=None):
            calls.append(1)
            return "stocks", [(D(2026, 10, 2), 1.0)]          # the source only ever has Friday's close

        morning = dt.datetime(2026, 10, 5, 14, 0, tzinfo=UTC)   # Monday 10:00 ET: Friday is the newest close
        evening = dt.datetime(2026, 10, 5, 21, 0, tzinfo=UTC)   # Monday 17:00 ET: Monday's close is due
        with tempfile.TemporaryDirectory() as tmp, Patch(fp, CACHE_DIR=Path(tmp), nasdaq_series=nas):
            fp.get_series("AAA", D(2025, 12, 18), D(2026, 10, 5), now=morning)
            fp.get_series("AAA", D(2025, 12, 18), D(2026, 10, 5), now=morning)
            self.assertEqual(len(calls), 1, "a fresh cache with the newest close must be reused")
            fp.get_series("AAA", D(2025, 12, 18), D(2026, 10, 5), now=evening)
            self.assertEqual(len(calls), 2, "after the close was due, a cache without it must be refetched")


class BenchmarkLimit(unittest.TestCase):
    def test_more_than_two_benchmarks_are_cut_with_a_warning(self):
        d = json.loads((ROOT / "examples" / "sample_prices.json").read_text(encoding="utf-8"))
        bench = d["series"]["BNCH"]
        for name in ("B2", "B3"):
            d["series"][name] = dict(bench)
        d["benchmarks"] = ["BNCH", "B2", "B3"]
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "p.json").write_text(json.dumps(d))
            _, series, benches, _, _, _, warnings = rc.load({"data": "p.json", "symbols": ["ACRB"]}, Path(tmp))
        self.assertEqual([b.sym for b in benches], ["BNCH", "B2"])
        self.assertTrue(any("3 benchmarks given" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
