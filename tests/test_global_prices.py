"""Market routing, exchange field mappings, session dates and truthful chart labels."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import fetch_prices as fp
import render_chart as rc

D = dt.date


class GlobalPrices(unittest.TestCase):
    def test_exchange_field_mappings_and_sources(self):
        sh = {"code": "600519", "kline": [[20260102, 10, 30, 5, 20, 100], [20260105, 11, 31, 6, 21, 100]]}
        sz = {"code": "0", "data": {"code": "000001", "picupdata": [
            ["2026-01-02", "10", "20", "5", "30"], ["2026-01-05", "11", "21", "6", "31"]]}}
        with patch.object(fp, "get_json", return_value=sh):
            a = fp.exchange_series("600519.SS")
        with patch.object(fp, "get_json", return_value=sz):
            b = fp.exchange_series("000001.SZ")
        self.assertEqual(a["points"], b["points"])
        self.assertEqual(a["points"][0], (D(2026, 1, 2), 20))
        self.assertEqual(a["exchange"], "XSHG")
        self.assertEqual(b["exchange"], "XSHE")
        self.assertEqual(a["adjustment"], "unadjusted")
        self.assertEqual(a["currency"], "CNY")
        with patch.object(fp, "get_json", return_value=sh), self.assertRaises(LookupError):
            fp.exchange_series("600000.SS")

    def test_auto_routes_without_falling_back_from_a_shares(self):
        entry = {"class": "stocks", "source": "test", "currency": "JPY", "points": [(D(2026, 1, 2), 10)]}
        with tempfile.TemporaryDirectory() as tmp, patch.object(fp, "CACHE_DIR", Path(tmp)), \
                patch.object(fp, "exchange_series", return_value=entry) as exchange, \
                patch.object(fp, "yahoo_series", return_value=entry) as yahoo, \
                patch.object(fp, "nasdaq_series", return_value=("stocks", entry["points"])) as nasdaq:
            for symbol in ("600519.SS", "000001.SZ"):
                fp.get_series(symbol, D(2026, 1, 1), D(2026, 2, 1), refresh=True)
            for symbol in ("7203.T", "0700.HK", "SAP.DE", "^HSI"):
                fp.get_series(symbol, D(2026, 1, 1), D(2026, 2, 1), refresh=True)
            fp.get_series("AAPL", D(2026, 1, 1), D(2026, 2, 1), refresh=True)
            self.assertEqual(exchange.call_count, 2)
            self.assertEqual(yahoo.call_count, 4)
            self.assertEqual(nasdaq.call_count, 1)
            for symbol in ("600519", "7203", "920001.BJ"):
                with self.assertRaises(LookupError):
                    fp.get_series(symbol, D(2026, 1, 1), D(2026, 2, 1))
            exchange.side_effect = fp.FetchError("exchange unavailable")
            with self.assertRaises(fp.FetchError):
                fp.get_series("600000.SS", D(2026, 1, 1), D(2026, 2, 1))
            self.assertEqual(yahoo.call_count, 4)

    def test_yahoo_exchange_date_nulls_and_unfinished_bar(self):
        # UTC Dec 31 23:00 is Jan 1 in Tokyo; do not attach it to Dec 31.
        stamp = int(dt.datetime(2025, 12, 31, 23, tzinfo=dt.timezone.utc).timestamp())
        data = {"chart": {"result": [{"meta": {"exchangeTimezoneName": "Asia/Tokyo", "gmtoffset": 32400, "currency": "JPY", "instrumentType": "ETF"},
                 "timestamp": [stamp, stamp + 86400], "indicators": {"quote": [{"close": [100, None]}]}}]}}
        with patch.object(fp, "get_json", return_value=data):
            a = fp.yahoo_series("7203.T", D(2025, 12, 31), D(2026, 1, 3))
        self.assertEqual(a["points"], [(D(2026, 1, 1), 100)])
        self.assertEqual(a["class"], "etf")
        self.assertEqual(a["currency"], "JPY")
        raw = data["chart"]["result"][0]
        raw["indicators"]["quote"][0]["close"][1] = 200
        raw["meta"]["currentTradingPeriod"] = {"regular": {"end": stamp + 86400 + 3600}}
        with patch.object(fp, "get_json", return_value=data), patch.object(fp.time, "time", return_value=stamp + 86400):
            a = fp.yahoo_series("7203.T", D(2025, 12, 31), D(2026, 1, 3))
        self.assertEqual(a["points"], [(D(2026, 1, 1), 100)])

    def test_invalid_closes_and_missing_symbols_are_errors(self):
        for value in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(fp.FetchError):
                fp.clean_points([(D(2026, 1, 1), value)])
        with patch.object(fp, "get_json", return_value={"chart": {"result": None, "error": "Not Found"}}), self.assertRaises(LookupError):
            fp.yahoo_series("UNKNOWN.T", D(2026, 1, 1), D(2026, 2, 1))

    def test_transient_network_error_is_retried(self):
        with patch.object(fp, "http_get", side_effect=[fp.FetchError("HTTP 429"), '{"ok": true}']) as request, \
                patch.object(fp.time, "sleep") as sleep:
            self.assertEqual(fp.get_json("https://example.test"), {"ok": True})
        self.assertEqual(request.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_long_exchange_holiday_does_not_require_a_missing_close(self):
        series = rc.Series("000001.SZ", [("2026-09-30", 10), ("2026-10-09", 11)], D(2026, 10, 8), D(2026, 10, 10))
        self.assertEqual(series.base_date, D(2026, 9, 30))
        self.assertAlmostEqual(series.ret, 10)

    def test_short_history_is_not_reported_as_full_period(self):
        entry = {"class": "stocks", "source": "exchange", "points": [["2026-01-02", 10], ["2026-01-05", 11]],
                 "fetched_at": "2026-01-06T00:00:00+00:00", "currency": "CNY"}
        with patch.object(fp, "get_series", return_value=(entry, None)), patch.object(fp.time, "sleep"):
            out = fp.build(["000001.SZ"], [], D(2025, 1, 1), D(2026, 2, 1), D(2026, 2, 1))
        self.assertEqual(out["series"], {})
        self.assertIn("no close within", out["errors"][0])

    def test_chart_currency_source_and_each_last_date(self):
        root = Path(__file__).resolve().parent.parent
        data = json.loads((root / "examples/sample_prices.json").read_text())
        data["series"]["ACRB"].update(currency="JPY", source="Yahoo Finance (aggregated daily closes)")
        data["series"]["STRK"].update(currency="CNY", adjustment="unadjusted", source="Shenzhen Stock Exchange (official website, unadjusted closes)")
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "prices.json").write_text(json.dumps(data))
            spec = {"data": "prices.json", "symbols": ["ACRB", "STRK"]}
            d, series, benches, base, end, start, warnings = rc.load(spec, Path(tmp))
            en = rc.build_html(spec, d, series, benches, base, end, start, "en")
            zh = rc.build_html(spec, d, series, benches, base, end, start, "zh")
        self.assertIn("JPY ", en)
        self.assertIn("CNY ", en)
        self.assertNotIn("price ($)", en)
        self.assertNotIn("computed from official closing prices", en)
        self.assertIn("Last close by symbol", en)
        self.assertTrue("未復權" in zh)
        self.assertTrue("聚合日收盤價" in zh)


if __name__ == "__main__":
    unittest.main()
