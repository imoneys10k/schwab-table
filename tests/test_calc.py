"""Known-answer tests for the calculations and parsers. Standard library only: python3 -m unittest discover -s tests -v"""
import datetime as dt
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import csv_to_prices  # noqa: E402
import fetch_prices  # noqa: E402
import render_chart as rc  # noqa: E402

D = dt.date


class SeriesMath(unittest.TestCase):
    def make(self, closes, base=D(2025, 12, 31), end=D(2026, 12, 31), start_day=D(2025, 12, 31)):
        pts = [((start_day + dt.timedelta(days=i)).isoformat(), c) for i, c in enumerate(closes)]
        return rc.Series("X", pts, base, end)

    def test_return_is_relative_to_base_close(self):
        s = self.make([100, 110, 99, 121])           # base = 12/31 close = 100
        self.assertAlmostEqual(s.ret, 21.0)
        self.assertEqual(s.idx[0], 100)
        self.assertAlmostEqual(s.idx[3], 121.0)

    def test_drawdown_known_answer(self):
        s = self.make([100, 110, 99, 121])
        self.assertAlmostEqual(s.dd[2], (99 / 110 - 1) * 100)   # -10%
        self.assertAlmostEqual(s.mdd, -10.0)
        self.assertEqual(s.dd[0], 0)
        self.assertEqual(s.dd[3], 0)                              # new high

    def test_volatility_known_answer(self):
        s = self.make([100, 110, 99, 121])
        r = [110 / 100 - 1, 99 / 110 - 1, 121 / 99 - 1]
        m = sum(r) / 3
        expect = math.sqrt(sum((x - m) ** 2 for x in r) / 2) * math.sqrt(252) * 100
        self.assertAlmostEqual(s.vol, expect)

    def test_base_is_last_close_on_or_before_start(self):
        # start Jan 1 (a holiday): the base must be the Dec 31 close, not a later one
        pts = [("2025-12-30", 90.0), ("2025-12-31", 100.0), ("2026-01-02", 105.0), ("2026-01-05", 110.0)]
        s = rc.Series("X", pts, D(2026, 1, 1), D(2026, 1, 31))
        self.assertEqual(s.base_date, D(2025, 12, 31))
        self.assertAlmostEqual(s.ret, 10.0)

    def test_base_is_on_the_start_date_when_it_is_a_trading_day(self):
        pts = [("2026-03-02", 50.0), ("2026-03-03", 55.0)]
        s = rc.Series("X", pts, D(2026, 3, 2), D(2026, 3, 31))
        self.assertEqual(s.base_date, D(2026, 3, 2))
        self.assertAlmostEqual(s.ret, 10.0)

    def test_missing_base_raises_instead_of_guessing(self):
        pts = [("2026-02-01", 50.0), ("2026-02-02", 55.0)]
        with self.assertRaises(ValueError):
            rc.Series("X", pts, D(2026, 1, 1), D(2026, 3, 1))       # no close within 7 days before the base

    def test_end_trims_later_closes(self):
        pts = [("2025-12-31", 100.0), ("2026-01-02", 110.0), ("2026-02-02", 200.0)]
        s = rc.Series("X", pts, D(2026, 1, 1), D(2026, 1, 31))
        self.assertAlmostEqual(s.ret, 10.0)
        self.assertEqual(s.dates[-1], D(2026, 1, 2))

    def test_unsorted_input_is_sorted(self):
        pts = [("2026-01-02", 110.0), ("2025-12-31", 100.0)]
        self.assertAlmostEqual(rc.Series("X", pts, D(2026, 1, 1), D(2026, 1, 31)).ret, 10.0)


class Scales(unittest.TestCase):
    def test_nice_ticks_stay_inside_range_and_are_sorted(self):
        for lo, hi in [(80, 200), (92.5, 108.1), (0, 1000), (-40, 0)]:
            t = rc.nice_ticks(lo, hi)
            self.assertTrue(all(lo - 1e-6 <= x <= hi + 1e-6 for x in t), (lo, hi, t))
            self.assertEqual(t, sorted(t))
            self.assertGreaterEqual(len(t), 3)

    def test_nice_ticks_include_100_for_a_typical_index_range(self):
        self.assertIn(100, rc.nice_ticks(85, 190))

    def test_log_ticks_in_range(self):
        t = rc.log_ticks(60, 400)
        self.assertTrue(all(60 * 0.999 <= x <= 400 * 1.001 for x in t))
        self.assertIn(100, t)
        self.assertLessEqual(len(t), 8)

    def test_spread_enforces_minimum_gap_and_keeps_order(self):
        out = rc.spread([("a", 100), ("b", 102), ("c", 104), ("d", 300)], 16, 400)
        ys = [out[k] for k in "abcd"]
        self.assertTrue(all(b - a >= 16 - 1e-9 for a, b in zip(ys, ys[1:])))
        self.assertEqual(out["d"], 300)

    def test_spread_pulls_back_labels_pushed_past_the_bottom(self):
        out = rc.spread([("a", 380), ("b", 385), ("c", 390)], 16, 400)
        self.assertLessEqual(max(out.values()), 400)

    def test_auto_log_threshold(self):
        def s(vals):
            return rc.Series("X", [("2025-12-31", 100.0)] + [(f"2026-01-{i + 2:02d}", v) for i, v in enumerate(vals)], D(2026, 1, 1), D(2026, 12, 31))
        self.assertFalse(rc.use_log({}, [s([110, 150, 120])]))
        self.assertTrue(rc.use_log({}, [s([110, 350, 120])]))
        self.assertTrue(rc.use_log({"y_scale": "log"}, [s([110])]))
        self.assertFalse(rc.use_log({"y_scale": "linear"}, [s([110, 350])]))

    def test_ytd_detection(self):
        self.assertTrue(rc.is_ytd(D(2026, 1, 1), D(2026, 10, 2)))
        self.assertFalse(rc.is_ytd(D(2026, 3, 2), D(2026, 10, 2)))

    def test_x_ticks_granularity(self):
        L = rc.S["en"]
        self.assertTrue(all(lab.count("/") == 1 for _, lab in rc.x_ticks(D(2026, 9, 1), D(2026, 10, 2), L)))   # weekly
        self.assertEqual(len(rc.x_ticks(D(2026, 1, 1), D(2026, 10, 2), L)), 10)                               # monthly
        self.assertTrue(all(len(lab) == 4 for _, lab in rc.x_ticks(D(2018, 1, 1), D(2026, 10, 2), L)))        # yearly


class Parsers(unittest.TestCase):
    def test_nasdaq_number_and_date_formats(self):
        self.assertEqual(fetch_prices.parse_close("$1,074.89"), 1074.89)
        self.assertEqual(fetch_prices.parse_close("27,190.86"), 27190.86)
        self.assertEqual(fetch_prices.parse_date("10/02/2026"), D(2026, 10, 2))

    def test_symbol_prefixes_and_index_codes(self):
        self.assertEqual(fetch_prices.split_symbol("etf:spy"), ("SPY", "etf"))
        self.assertEqual(fetch_prices.split_symbol("index:COMP"), ("COMP", "index"))
        self.assertEqual(fetch_prices.split_symbol("nvda"), ("NVDA", None))
        self.assertIn("COMP", fetch_prices.INDEX_SYMBOLS)       # COMP must not be looked up as the stock Compass Inc
        with self.assertRaises(LookupError):
            fetch_prices.split_symbol("foo:BAR")

    def test_non_us_symbols_get_a_clear_error_without_a_network_call(self):
        for s in ("0700.HK", "600519.SS", "600519"):
            with self.assertRaises(LookupError) as cm:
                fetch_prices.nasdaq_series(s, D(2026, 1, 1), D(2026, 10, 1))
            self.assertIn("csv_to_prices.py", str(cm.exception))

    def test_cache_round_trip_and_expiry(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = fetch_prices.CACHE_DIR
            fetch_prices.CACHE_DIR = Path(tmp)
            try:
                self.assertEqual(fetch_prices.cache_read("AAA", D(2026, 1, 1)), (None, None))
                fetch_prices.cache_write("AAA", D(2026, 1, 1), {"class": "stocks", "points": [["2026-01-02", 1.0]]})
                d, age = fetch_prices.cache_read("AAA", D(2026, 1, 1))
                self.assertEqual(d["points"], [["2026-01-02", 1.0]])
                self.assertLess(age, 5)
            finally:
                fetch_prices.CACHE_DIR = old

    def test_stale_cache_is_used_when_the_network_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            old_dir, old_nas = fetch_prices.CACHE_DIR, fetch_prices.nasdaq_series
            fetch_prices.CACHE_DIR = Path(tmp)

            def boom(*a, **k):
                raise fetch_prices.FetchError("offline")
            fetch_prices.nasdaq_series = boom
            try:
                fetch_prices.cache_write("AAA", D(2025, 12, 18), {"class": "stocks", "source": "x", "points": [["2026-01-02", 1.0]], "fetched_at": "2026-01-03T00:00:00+00:00"})
                p = fetch_prices.cache_path("AAA", D(2025, 12, 18))
                data = json.loads(p.read_text())
                data["saved_at"] -= 10 * 24 * 3600                       # older than the TTL
                p.write_text(json.dumps(data))
                entry, warn = fetch_prices.get_series("AAA", D(2025, 12, 18), D(2026, 10, 1))
                self.assertIn("using cached data", warn)
                self.assertEqual(entry["points"], [["2026-01-02", 1.0]])
                with self.assertRaises(fetch_prices.FetchError):          # no cache at all -> the error surfaces
                    fetch_prices.get_series("BBB", D(2025, 12, 18), D(2026, 10, 1))
            finally:
                fetch_prices.CACHE_DIR, fetch_prices.nasdaq_series = old_dir, old_nas


class CsvImport(unittest.TestCase):
    def write(self, tmp, name, text):
        p = Path(tmp) / name
        p.write_text(text, encoding="utf-8")
        return str(p)

    def test_common_formats(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self.write(tmp, "a.csv", "Date,Open,Close\n2026-01-02,1,10.5\n2026-01-05,1,\"1,011.25\"\n")
            b = self.write(tmp, "b.csv", "Date,Close/Last,Volume\n01/05/2026,$20.00,5\n01/02/2026,$19.00,7\n")
            c = self.write(tmp, "c.csv", "日期,收盘价\n20260102,3.5\n20260105,3.6\n")
            self.assertEqual(csv_to_prices.read_csv(a), [(D(2026, 1, 2), 10.5), (D(2026, 1, 5), 1011.25)])
            self.assertEqual(csv_to_prices.read_csv(b), [(D(2026, 1, 2), 19.0), (D(2026, 1, 5), 20.0)])      # sorted ascending
            self.assertEqual(csv_to_prices.read_csv(c), [(D(2026, 1, 2), 3.5), (D(2026, 1, 5), 3.6)])

    def test_adj_close_marks_total_return(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = self.write(tmp, "a.csv", "Date,Close,Adj Close\n2026-01-02,10,9\n2026-01-05,11,10\n")
            out = csv_to_prices.build([("AAA", a)], [], adj=True)
            self.assertEqual(out["series"]["AAA"]["basis"], "total")
            self.assertEqual(out["series"]["AAA"]["points"][0][1], 9.0)
            self.assertEqual(csv_to_prices.build([("AAA", a)], [], adj=False)["series"]["AAA"]["basis"], "price")

    def test_bad_input_is_rejected_with_a_clear_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            no_close = self.write(tmp, "n.csv", "Date,Volume\n2026-01-02,1\n2026-01-03,2\n")
            bad_date = self.write(tmp, "d.csv", "Date,Close\nyesterday,1\n2026-01-03,2\n")
            for p in (no_close, bad_date):
                with self.assertRaises(ValueError):
                    csv_to_prices.read_csv(p)
            with self.assertRaises(ValueError):
                csv_to_prices.read_csv(self.write(tmp, "short.csv", "Date,Close\n2026-01-02,1\n"))


class EndToEnd(unittest.TestCase):
    """Render the committed sample data to HTML (no browser needed) and check the structure and numbers."""

    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((ROOT / "examples" / "chart_lines_spec.json").read_text(encoding="utf-8"))
        cls.base = ROOT / "examples"

    def load(self, spec):
        return rc.load(spec, self.base)

    def test_lines_html_contains_the_expected_numbers(self):
        d, series, benches, base, end, start, w = self.load(self.spec)
        html = rc.build_html(self.spec, d, series, benches, base, end, start, "en")
        self.assertIn("2026 YTD Price Performance", html)
        self.assertIn("+88.4%", html)                                  # ACRB, the target built into the sample data
        self.assertIn("Past performance is no guarantee", html)
        self.assertNotIn("None", html)
        self.assertEqual(html.count('class="hov"'), 1)

    def test_every_symbol_has_a_direct_label_and_a_table_row(self):
        d, series, benches, base, end, start, w = self.load(self.spec)
        html = rc.build_html(self.spec, d, series, benches, base, end, start, "en")
        for s in series:
            self.assertIn(f"({s.sym})</td>", html)
            self.assertIn(f'<tspan font-weight="700">{s.sym}</tspan>', html)

    def test_multiples_layout_and_dark_theme(self):
        spec = json.loads((ROOT / "examples" / "chart_multiples_spec.json").read_text(encoding="utf-8"))
        d, series, benches, base, end, start, w = self.load(spec)
        html = rc.build_html(spec, d, series, benches, base, end, start, "zh", "dark")
        self.assertTrue("對數刻度" in html)                             # WAYN's +241% triggers the automatic log scale
        self.assertIn(rc.THEMES["dark"]["bg"], html)
        self.assertEqual(html.count('class="hov"'), len(series))

    def test_colors_follow_the_symbol_not_the_rank(self):
        d, series, benches, base, end, start, w = self.load(self.spec)
        reordered = dict(self.spec, symbols=list(reversed(self.spec["symbols"])))
        d2, series2, benches2, *_ = self.load(reordered)
        c1 = rc.Ctx(self.spec, d, series, benches, base, end, start, "en", "light")
        c2 = rc.Ctx(reordered, d2, series2, benches2, base, end, start, "en", "light")
        # the fixed order is the order the user lists symbols in, so reversing the list reverses the colours
        self.assertEqual(c1.col[series[0].sym], rc.THEMES["light"]["ser"][0])
        self.assertEqual(c2.col[series2[0].sym], rc.THEMES["light"]["ser"][0])
        self.assertNotEqual(c1.col["ACRB"], c2.col["ACRB"])

    def test_custom_colors_are_validated(self):
        with self.assertRaises(SystemExit):
            self.load(dict(self.spec, colors={"ACRB": "red"}))
        ok = self.load(dict(self.spec, colors={"ACRB": "#112233"}))
        c = rc.Ctx(dict(self.spec, colors={"ACRB": "#112233"}), ok[0], ok[1], ok[2], ok[3], ok[4], ok[5], "en", "light")
        self.assertEqual(c.col["ACRB"], "#112233")

    def test_mixing_price_and_total_return_is_refused(self):
        d = json.loads((self.base / "sample_prices.json").read_text(encoding="utf-8"))
        d["series"]["ACRB"]["basis"] = "total"
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "p.json").write_text(json.dumps(d))
            with self.assertRaises(SystemExit):
                rc.load({"data": "p.json", "symbols": ["ACRB", "STRK"]}, Path(tmp))

    def test_sample_data_hits_its_built_in_targets(self):
        d, series, benches, *_ = self.load({"data": "sample_prices.json"})
        got = {s.sym: round(s.ret, 1) for s in series}
        self.assertEqual(got["ACRB"], 88.4)
        self.assertEqual(got["WAYN"], 241.0)
        self.assertEqual(round(benches[0].ret, 1), 12.8)


if __name__ == "__main__":
    unittest.main()
