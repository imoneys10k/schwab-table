"""ETF holdings: issuer parsers, routing, cache, and the top-N ranking rules. Offline; standard library only (+ OpenCC for zh output)."""
import datetime as dt
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fetch_holdings as fh  # noqa: E402
import render_holdings as rh  # noqa: E402
sys.path.insert(0, str(ROOT / "tools"))
import live_check as lc  # noqa: E402

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 10, 12, 12, 0, tzinfo=UTC)


class Patch:
    def __init__(self, module, **attrs):
        self.module, self.attrs, self.saved = module, attrs, {}

    def __enter__(self):
        for k, v in self.attrs.items():
            self.saved[k] = getattr(self.module, k)
            setattr(self.module, k, v)

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            setattr(self.module, k, v)


def make_xlsx(rows):
    """Minimal one-sheet xlsx with shared strings, enough to exercise the SSGA reader."""
    strings, body = [], []
    for n, row in enumerate(rows, 1):
        cells = []
        for col, v in zip("ABCDEFGH", row):
            if isinstance(v, str):
                strings.append(v)
                cells.append(f'<c r="{col}{n}" t="s"><v>{len(strings) - 1}</v></c>')
            elif v is not None:
                cells.append(f'<c r="{col}{n}"><v>{v}</v></c>')
        body.append(f'<row r="{n}">{"".join(cells)}</row>')
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("xl/sharedStrings.xml", "<sst>" + "".join(f"<si><t>{s.replace('&', '&amp;')}</t></si>" for s in strings) + "</sst>")
        z.writestr("xl/worksheets/sheet1.xml", f"<worksheet><sheetData>{''.join(body)}</sheetData></worksheet>")
    return buf.getvalue()


def h(ticker, name, weight, kind="equity", ident=None, sector=None, **extra):
    return {"ticker": ticker, "name": name, "weight": weight, "sector": sector, "kind": kind, "id": ident or ticker or name, **extra}


def fund(rows, **kw):
    return {"symbol": "TST", "name": "Test ETF", "issuer": "Test", "issuer_key": "test", "as_of": "2026-10-09", "source": "Test file",
            "source_url": "", "weight_basis": "% of net assets", "holdings": rows, "warnings": [], "retrieved_at": "2026-10-12T00:00:00+00:00", **kw}


class Parsing(unittest.TestCase):
    def test_pct(self):
        self.assertEqual(fh.pct("8.07%"), 8.07)
        self.assertEqual(fh.pct("1,234.5"), 1234.5)
        self.assertEqual(fh.pct("-0.48%"), -0.48)
        for blank in ("", "-", "NA", None, "n/a", "abc"):
            self.assertIsNone(fh.pct(blank))

    def test_parse_date(self):
        D = dt.date
        self.assertEqual(fh.parse_date("2026-08-31T00:00:00-04:00"), D(2026, 8, 31))
        self.assertEqual(fh.parse_date("Oct 09, 2026"), D(2026, 10, 9))
        self.assertEqual(fh.parse_date("09-Oct-2026"), D(2026, 10, 9))
        self.assertEqual(fh.parse_date("10/12/2026"), D(2026, 10, 12))
        self.assertEqual(fh.parse_date("June 30, 2026"), D(2026, 6, 30))
        self.assertIsNone(fh.parse_date("soon"))

    def test_ssga_reads_rows_and_stops_at_the_disclaimer(self):
        blob = make_xlsx([["Fund Name:", "SPDR Test ETF"], ["Ticker Symbol:", "TST"], ["Holdings:", "As of 09-Oct-2026"], [],
                          ["Name", "Ticker", "Identifier", "SEDOL", "Weight", "Sector", "Shares Held", "Local Currency"],
                          ["NVIDIA CORP", "NVDA", "67066G104", "2379504", "8.24", "-", "2.9E8", "USD"],
                          ["US DOLLAR", "-", "USD", "-", "0.28", "-", "1", "USD"],
                          ["Disclaimer text that is long and has no weight"]])
        res = fh.parse_ssga("TST", blob, "u")
        self.assertEqual(res["as_of"], "2026-10-09")
        self.assertEqual(res["name"], "SPDR Test ETF")
        self.assertEqual([(x["ticker"], x["kind"]) for x in res["holdings"]], [("NVDA", "equity"), ("", "cash")])
        self.assertIsNone(res["holdings"][0]["sector"])  # '-' is not a sector

    def test_ssga_rejects_a_file_for_another_ticker(self):
        blob = make_xlsx([["Fund Name:", "X"], ["Ticker Symbol:", "ZZZ"], ["Holdings:", "As of 09-Oct-2026"],
                          ["Name", "Ticker", "Identifier", "SEDOL", "Weight"], ["A", "A", "1", "2", "1.0"]])
        with self.assertRaises(fh.FetchError):
            fh.parse_ssga("TST", blob, "u")

    def test_ishares_kinds_and_header(self):
        text = ('iShares Core S&P 500 ETF\nFund Holdings as of,"Oct 09, 2026"\nInception Date,"May 15, 2000"\n\n'
                'Ticker,Name,Sector,Asset Class,Market Value,Weight (%),Notional Value\n'
                '"NVDA","NVIDIA","Information Technology","Equity","1","8.23","1"\n'
                '"USD","USD CASH","Cash and/or Derivatives","Cash","1","0.05","1"\n'
                '"ESZ6","S&P500 EMINI DEC 26","Cash and/or Derivatives","Futures","0","0.00","0"\n')
        res = fh.parse_ishares("IVV", text, "u")
        self.assertEqual(res["name"], "iShares Core S&P 500 ETF")
        self.assertEqual(res["as_of"], "2026-10-09")
        self.assertEqual([x["kind"] for x in res["holdings"]], ["equity", "cash", "other"])

    def test_ishares_bond_fund_has_no_ticker_column(self):
        """Regression: AGG and TLT failed with 'no holdings table' because their header starts with Name, not Ticker."""
        text = ('iShares Core U.S. Aggregate Bond ETF\nFund Holdings as of,"Oct 09, 2026"\n\n'
                'Name,Sector,Asset Class,Market Value,Weight (%),Par Value,CUSIP,ISIN,Maturity,Coupon (%)\n'
                '"BLACKROCK CASH CL INST SL AGENCY","Cash and/or Derivatives","Money Market","1","3.05","1","066922519","US0669225197","-","-"\n'
                '"TREASURY NOTE","Treasury","Fixed Income","1","0.40","1","91282CGQ8","US91282CGQ87","Feb 28, 2030","4.00"\n'
                '"TREASURY NOTE","Treasury","Fixed Income","1","0.35","1","91282CHB0","US91282CHB09","Mar 31, 2030","3.50"\n')
        res = fh.parse_ishares("AGG", text, "u")
        self.assertEqual([x["kind"] for x in res["holdings"]], ["cash", "bond", "bond"])
        self.assertEqual([x["name"] for x in res["holdings"][1:]], ["TREASURY NOTE 4% Feb 28, 2030", "TREASURY NOTE 3.5% Mar 31, 2030"])
        ranked, excluded, _ = rh.build_rows(res)
        self.assertEqual(len(ranked), 2)  # the bonds are ranked, the money-market line is not
        self.assertEqual(excluded, {"cash": 3.05})

    def test_vanguard_joins_pages_and_keeps_missing_weights_as_none(self):
        page1 = {"asOfDate": "2026-08-31T00:00:00-04:00", "fund": {"entity": [{"ticker": "NVDA", "longName": "NVIDIA Corp.", "percentWeight": "8.08", "cusip": "67066G104"}]}}
        page2 = {"asOfDate": "2026-08-31T00:00:00-04:00", "fund": {"entity": [{"ticker": "BF.B", "longName": "Brown-Forman", "percentWeight": ""}]}}
        res = fh.parse_vanguard("VOO", [page1, page2], "u")
        self.assertEqual(res["as_of"], "2026-08-31")
        self.assertEqual([x["weight"] for x in res["holdings"]], [8.08, None])

    def test_neos_and_roundhill_csv(self):
        text = ("Date,Account,StockTicker,Cusip,SecurityName,Shares,Price,MarketValue,Weightings,NetAssets,SharesOutstanding,CreationUnits,MoneyMarketFlag\n"
                '10/12/2026,TST,MU,595112103,"Micron Technology Inc",1,1,1,4.44%,1,1,1,\n'
                '10/12/2026,TST,595112103 TRS 052427 GS,595112103 TRS 052427 GS,"MICRON TECHNOLOGY, INC.-SWAP-GOLD-L",1,1,1,10.49%,1,1,1,\n'
                '10/12/2026,TST,912797VA2,912797VA2,United States Treasury Bill 12/03/2026,1,1,1,12.65%,1,1,1,\n'
                '10/12/2026,TST,FGXXX,31846V336,First American Government Obligations Fund,1,1,1,13.34%,1,1,1,Y\n'
                '10/12/2026,TST,NDX   261120C31325000,NDX US 11/20/26 C31325,NDX US 11/20/26 C31325,1,1,1,-0.48%,1,1,1,\n'
                '10/12/2026,TST,Cash&Other,Cash&Other,Cash & Other,1,1,1,-50.48%,1,1,1,Y\n'
                '10/12/2026,OTHER,AAPL,037833100,Apple Inc,1,1,1,9.00%,1,1,1,\n')
        res = fh.parse_neos_like("TST", "roundhill", text, "u", "src")
        kinds = {x["name"]: x["kind"] for x in res["holdings"]}
        self.assertEqual(len(res["holdings"]), 6)  # the other fund's row is not mixed in
        self.assertEqual(kinds["Micron Technology Inc"], "equity")
        self.assertEqual(kinds["MICRON TECHNOLOGY, INC."], "swap")
        self.assertEqual(kinds["United States Treasury Bill 12/03/2026"], "treasury")
        self.assertEqual(kinds["First American Government Obligations Fund"], "cash")
        self.assertEqual(kinds["NDX US 11/20/26 C31325"], "option")
        self.assertEqual(kinds["Cash & Other"], "cash")
        swap = next(x for x in res["holdings"] if x["kind"] == "swap")
        self.assertEqual(swap["underlying_id"], "595112103")
        # stamped Monday 10/12, but the prices in such files are the previous (Friday 10/09) close
        self.assertEqual((res["as_of"], res["issuer_date"]), ("2026-10-09", "2026-10-12"))
        res = fh.parse_neos_like("TST", "roundhill", text, "u", "src", valuation_date=dt.date(2026, 10, 9))
        self.assertEqual((res["as_of"], res["issuer_date"]), ("2026-10-09", "2026-10-12"))
        with self.assertRaises(fh.NotThisIssuer):
            fh.parse_neos_like("NOPE", "roundhill", text, "u", "src")

    def test_prev_weekday_skips_weekends(self):
        D = dt.date
        self.assertEqual(fh.prev_weekday(D(2026, 10, 12)), D(2026, 10, 9))   # Monday -> Friday
        self.assertEqual(fh.prev_weekday(D(2026, 10, 13)), D(2026, 10, 12))
        self.assertEqual(fh.prev_weekday(D(2026, 10, 10)), D(2026, 10, 9))   # Saturday -> Friday

    def test_prices_are_kept_for_equities_only(self):
        text = ("Date,Account,StockTicker,Cusip,SecurityName,Shares,Price,MarketValue,Weightings,NetAssets,SharesOutstanding,CreationUnits,MoneyMarketFlag\n"
                '10/12/2026,TST,AAPL,037833100,Apple Inc,1,"$1,029.50",1,5.00%,1,1,1,\n'
                '10/12/2026,TST,912797VA2,912797VA2,United States Treasury Bill 12/03/2026,1,99.4,1,12.65%,1,1,1,\n')
        res = fh.parse_neos_like("TST", "neos", text, "u", "src")
        self.assertEqual(res["holdings"][0]["price"], 1029.5)
        self.assertNotIn("price", res["holdings"][1])

    def test_swap_names_lose_the_counterparty_suffix(self):
        for raw, want in (("MICRON TECHNOLOGY, INC.-SWAP-GOLD-L", "MICRON TECHNOLOGY, INC."), ("Nebius Group N.V. SWAP NM", "Nebius Group N.V."),
                          ("SK HYNIX INC-SWAP-GOLD-L", "SK HYNIX INC"), ("EVOLUTION AB (PUBL)-SWAP-NMRA-L", "EVOLUTION AB (PUBL)")):
            self.assertEqual(fh.swap_name(raw), want)

    def test_tema_csv_fractions_become_percent_and_swaps_are_marked(self):
        text = ("holdings_date,ticker,cusip,proper_name,shares,market_value,percent_of_nav,is_cash,country,sector\n"
                "2026-10-09,SNDK,80004C200,SANDISK CORP,8680,1,0.1845,0,United States,Information Technology\n"
                "2026-10-09,000660 KS,,SK HYNIX INC,10091,1,0.1698,0,South Korea,Information Technology\n"
                "2026-10-09,BTMTQT8-TRS-07/27/29-L-MREX,BTMTQT8-TRS-07/27/29-L-MREX,CHANGXIN MEMORY TECHNOLOGIES-SWAP-MREX-L,5,1,0.0568,0,,\n"
                "2026-10-09,,,CASH & CASH EQUIVALENTS,,-1,-0.019,1,,\n")
        res = fh.parse_tema("DISK", text, "u")
        self.assertEqual(res["as_of"], "2026-10-09")
        self.assertEqual([(x["kind"], x["weight"]) for x in res["holdings"]], [("equity", 18.45), ("equity", 16.98), ("swap", 5.68), ("cash", -1.9)])
        self.assertEqual(res["holdings"][2]["underlying_id"], "BTMTQT8")
        self.assertEqual(res["holdings"][1]["id"], "000660 KS")  # no CUSIP for Korean shares: fall back to the ticker
        self.assertEqual(res["holdings"][2]["name"], "CHANGXIN MEMORY TECHNOLOGIES")

    def test_tema_walks_back_to_the_last_published_day(self):
        asked = []
        csv_text = "holdings_date,ticker,cusip,proper_name,percent_of_nav,is_cash\n2026-10-09,AAA,111,Alpha Inc,1.0,0\n"

        def fake_fetch(url, **_):
            asked.append(url[-12:-4])
            if url.endswith("10092026.csv"):
                return csv_text
            raise fh.FetchError("HTTP 404")
        with Patch(fh, fetch=fake_fetch):
            res = fh.fetch_tema("DISK", now=NOW)
            self.assertEqual(asked, ["10122026", "10092026"])
            self.assertEqual(res["holdings"][0]["weight"], 100.0)

    def test_tema_unknown_fund_is_not_this_issuer(self):
        def never(url, **_):
            raise fh.FetchError("HTTP 404")
        with Patch(fh, fetch=never):
            with self.assertRaises(fh.NotThisIssuer):
                fh.fetch_tema("ZZZZ", now=NOW)

    def test_user_csv_with_holding_ticker_column(self):
        text = "Fund Ticker,Holding Ticker,Name,Weight,Sector\nQQQ,NVDA,NVIDIA Corp,8.25,Technology\nQQQ,AAPL,Apple Inc,7.34,Technology\n"
        res = fh.parse_user_csv("QQQ", text, "qqq.csv", "Invesco QQQ Trust")
        self.assertEqual([(x["ticker"], x["weight"]) for x in res["holdings"]], [("NVDA", 8.25), ("AAPL", 7.34)])

    def test_user_csv_with_preamble(self):
        text = "Fund,My ETF\nGenerated,today\nName,Ticker,Weight (%)\nApple Inc,AAPL,7.5\nCash,,1.0\nBad,BAD,n/a\n"
        res = fh.parse_user_csv("MYETF", text, "my.csv", "My ETF")
        self.assertEqual([x["name"] for x in res["holdings"]], ["Apple Inc", "Cash"])
        self.assertIn("as-of date unknown", res["warnings"][0])
        with self.assertRaises(fh.FetchError):
            fh.parse_user_csv("X", "a,b\n1,2\n", "bad.csv")


class Validation(unittest.TestCase):
    def test_validate_flags_partial_files_and_missing_weights(self):
        res = fund([h("A", "A", 40.0), h("B", "B", None)])
        fh.validate(res)
        self.assertTrue(any("add up to 40.0%" in w for w in res["warnings"]))
        self.assertTrue(any("no reported weight" in w for w in res["warnings"]))

    def test_validate_rejects_empty_and_weightless_files(self):
        with self.assertRaises(fh.FetchError):
            fh.validate(fund([]))
        with self.assertRaises(fh.FetchError):
            fh.validate(fund([h("A", "A", None)]))

    def test_stale_holdings_are_warned_about(self):
        with Patch(fh, fund_name=lambda s: "Fund"):
            res = fh.finish(fund([h("A", "A", 100.0)], as_of="2026-08-31"), NOW)
        self.assertTrue(any("42 days" in w for w in res["warnings"]))
        with Patch(fh, fund_name=lambda s: "Fund"):
            self.assertFalse(fh.finish(fund([h("A", "A", 100.0)], as_of="2026-10-09"), NOW)["warnings"])


class Routing(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.restore = Patch(fh, CACHE_DIR=Path(self.tmp.name), fund_name=lambda s: "Fund")
        self.restore.__enter__()

    def tearDown(self):
        self.restore.__exit__()
        self.tmp.cleanup()

    def ok(self, key):
        return lambda symbol, **_: fh.result(symbol, key, [h("A", "A", 100.0)], dt.date(2026, 10, 9), "src", "u")

    def test_known_tickers_go_to_their_issuer_only(self):
        calls = []
        adapters = {k: (lambda key: lambda symbol, **_: (calls.append(key), self.ok(key)(symbol))[1])(k) for k in fh.ADAPTERS}
        with Patch(fh, ADAPTERS=adapters):
            for sym, issuer in (("VOO", "vanguard"), ("SPY", "ssga"), ("IVV", "ishares"), ("QQQI", "neos"), ("NCLD", "roundhill"), ("DRAM", "roundhill"), ("DISK", "tema")):
                calls.clear()
                self.assertEqual(fh.get_holdings(sym, refresh=True, now=NOW)["issuer_key"], issuer)
                self.assertEqual(calls, [issuer])

    def test_issuers_that_forbid_automated_access_are_never_fetched(self):
        """Invesco's and Destiny's terms of use forbid automated access, so their funds must fail with import instructions, even with a cache."""
        calls = []
        adapters = {k: (lambda symbol, **_: calls.append(symbol)) for k in fh.ADAPTERS}
        with Patch(fh, ADAPTERS=adapters):
            for sym, name in (("QQQ", "Invesco"), ("QQQM", "Invesco"), ("DXYZ", "Destiny")):
                with self.assertRaises(fh.FetchError) as cm:
                    fh.get_holdings(sym, refresh=True, now=NOW)
                msg = str(cm.exception)
                self.assertIn(name, msg)
                self.assertIn("terms of use forbid automated access", msg)
                self.assertIn(f"fetch_holdings.py {sym} --csv", msg)
            with self.assertRaises(fh.FetchError):
                fh.get_holdings("SPY", issuer="invesco", now=NOW)
        self.assertEqual(calls, [])
        # a result cached before the rule existed must not be served either
        fh.cache_file("QQQ", None).write_text(json.dumps({"saved_at": 9e12, "data": {"symbol": "QQQ"}}), encoding="utf-8")
        with self.assertRaises(fh.FetchError):
            fh.get_holdings("QQQ", now=NOW)

    def test_unknown_tickers_are_never_probed_against_forbidden_hosts(self):
        self.assertNotIn("invesco", fh.ISSUER_ORDER)
        self.assertNotIn("destiny", fh.ISSUER_ORDER)
        self.assertEqual(set(fh.ADAPTERS) & set(fh.MANUAL), set())

    def test_unknown_ticker_is_probed_until_an_issuer_has_it(self):
        def miss(symbol, **_):
            raise fh.NotThisIssuer("not here")
        adapters = {k: miss for k in fh.ADAPTERS}
        adapters["neos"] = self.ok("neos")
        with Patch(fh, ADAPTERS=adapters):
            self.assertEqual(fh.get_holdings("ZZZZ", refresh=True, now=NOW)["issuer_key"], "neos")

    def test_unknown_everywhere_suggests_csv(self):
        def miss(symbol, **_):
            raise fh.NotThisIssuer("not here")
        with Patch(fh, ADAPTERS={k: miss for k in fh.ADAPTERS}):
            with self.assertRaises(fh.FetchError) as cm:
                fh.get_holdings("ZZZZ", refresh=True, now=NOW)
        self.assertIn("--csv", str(cm.exception))

    def test_a_network_failure_on_a_known_issuer_is_not_hidden_by_probing(self):
        def boom(symbol, **_):
            raise fh.FetchError("timeout")
        adapters = {k: self.ok(k) for k in fh.ADAPTERS}
        adapters["ssga"] = boom
        with Patch(fh, ADAPTERS=adapters):
            with self.assertRaises(fh.FetchError):
                fh.get_holdings("SPY", refresh=True, now=NOW)

    def test_cache_is_used_for_six_hours_and_refresh_bypasses_it(self):
        n = []

        def counted(symbol, **_):
            n.append(1)
            return self.ok("ssga")(symbol)
        with Patch(fh, ADAPTERS=dict(fh.ADAPTERS, ssga=counted)):
            fh.get_holdings("SPY", now=NOW)
            fh.get_holdings("SPY", now=NOW)
            self.assertEqual(len(n), 1)
            fh.get_holdings("SPY", refresh=True, now=NOW)
            self.assertEqual(len(n), 2)

    def test_roundhill_walks_back_over_missing_days(self):
        asked = []
        csv_text = "Date,Account,StockTicker,Cusip,SecurityName,Weightings,MoneyMarketFlag\n10/09/2026,TST,AAA,111,Alpha Inc,100%,\n"

        def fake_fetch(url, **_):
            asked.append(url[-12:-4])
            return csv_text if url.endswith("10092026.csv") else "<!doctype html><html>404</html>"
        with Patch(fh, fetch=fake_fetch):
            res = fh.fetch_roundhill("TST", now=NOW)  # Monday 12 Oct; weekends are skipped
        self.assertEqual(asked, ["10122026", "10092026"])
        self.assertEqual(res["holdings"][0]["name"], "Alpha Inc")


class Ranking(unittest.TestCase):
    def test_swaps_are_added_to_the_stock_and_cash_is_left_out(self):
        rows = [h("MU", "Micron", 4.0, ident="595"), h("SNDK", "Sandisk", 5.0, ident="777"),
                h("", "MICRON", 10.0, "swap", "595 TRS 1", underlying_id="595"), h("", "MICRON", 6.0, "swap", "595 TRS 2", underlying_id="595"),
                h("", "CXMT", 5.0, "swap", "CX TRS", underlying_id="CX"),
                h("", "T-Bill", 40.0, "treasury", "TB"), h("", "Cash", -30.0, "cash", "C")]
        ranked, excluded, notes = rh.build_rows(fund(rows))
        self.assertEqual([(r["name"], r["total"]) for r in ranked], [("Micron", 20.0), ("CXMT", 5.0), ("Sandisk", 5.0)])
        self.assertEqual((ranked[0]["physical"], ranked[0]["swap"]), (4.0, 16.0))
        self.assertEqual(excluded, {"treasury": 40.0, "cash": -30.0})
        self.assertTrue(notes["unmatched"])

    def test_lines_mode_ranks_everything_as_listed(self):
        rows = [h("A", "A", 5.0), h("", "T-Bill", 40.0, "treasury", "TB"), h("", "Swap", 10.0, "swap", "S", underlying_id="A")]
        ranked, excluded, _ = rh.build_rows(fund(rows), "lines")
        self.assertEqual([r["name"] for r in ranked], ["T-Bill", "Swap", "A"])
        self.assertEqual(excluded, {})

    def test_share_classes_merge_only_when_asked(self):
        rows = [h("GOOGL", "Alphabet Inc Class A", 3.1), h("GOOG", "Alphabet Inc Class C", 2.9), h("TSLA", "Tesla Inc", 3.0)]
        ranked, _, notes = rh.build_rows(fund(rows))
        self.assertEqual([r["name"] for r in ranked], ["Alphabet Inc Class A", "Tesla Inc", "Alphabet Inc Class C"])
        merged, _, notes = rh.build_rows(fund(rows), merge_classes=True)
        self.assertEqual((merged[0]["ticker"], round(merged[0]["total"], 2)), ("GOOGL / GOOG", 6.0))
        self.assertEqual(notes["merged"], ["Alphabet Inc Class A"])

    def test_same_name_without_a_class_marker_is_merged_too(self):
        """NEOS lists both Alphabet lines as 'Alphabet Inc'."""
        rows = [h("GOOGL", "Alphabet Inc", 3.1), h("GOOG", "Alphabet Inc", 2.9)]
        merged, _, _ = rh.build_rows(fund(rows), merge_classes=True)
        self.assertEqual(len(merged), 1)

    def test_missing_weights_are_not_ranked_and_not_zero(self):
        rows = [h("A", "A", 5.0), h("B", "B", None)]
        ranked, _, notes = rh.build_rows(fund(rows))
        self.assertEqual([r["name"] for r in ranked], ["A"])
        self.assertEqual(notes["na"], 1)

    def test_bond_funds_rank_their_bonds(self):
        rows = [h("", "UST 2030", 3.0, "bond", "b1"), h("", "UST 2035", 4.0, "bond", "b2"), h("", "Cash", 1.0, "cash", "c")]
        ranked, excluded, _ = rh.build_rows(fund(rows))
        self.assertEqual([r["name"] for r in ranked], ["UST 2035", "UST 2030"])
        self.assertEqual(excluded, {"cash": 1.0})

    def test_ranking_is_deterministic_on_ties(self):
        rows = [h("B", "Beta", 2.0), h("A", "Alpha", 2.0)]
        self.assertEqual([r["name"] for r in rh.build_rows(fund(rows))[0]], ["Alpha", "Beta"])


class Rendering(unittest.TestCase):
    def rows(self):
        return [h(f"T{i}", f"Company {i}", 10.0 - i, sector="Tech") for i in range(15)] + [h("", "Cash", 0.0, "cash", "c")]

    def test_summary_lines_and_cumulative_weights(self):
        html = rh.build_html(fund(self.rows()), "en", top=13)
        self.assertIn("Top 13 holdings", html)
        self.assertIn("All other holdings (2)", html)
        self.assertIn("Not ranked: cash", html)
        self.assertIn("Past performance is no guarantee of future results.", html)
        self.assertIn("Test ETF (TST)", html)

    def test_one_decimal_data_is_not_shown_with_two(self):
        one = fund([h("A", "A", 14.4), h("B", "B", 10.6)])
        self.assertIn(">14.4<", rh.build_html(one, "en"))
        two = fund([h("A", "A", 14.43), h("B", "B", 10.6)])
        self.assertIn(">14.43<", rh.build_html(two, "en"))

    def test_swap_view_has_legend_and_notice(self):
        rows = [h("A", "A", 5.0, ident="a"), h("", "A", 9.0, "swap", "a TRS", underlying_id="a"), h("", "Cash", -9.0, "cash", "c")]
        html = rh.build_html(fund(rows), "en")
        self.assertIn("Swap exposure", html)
        self.assertIn("Negative cash offsets", html)
        self.assertNotIn("Swap exposure", rh.build_html(fund([h("A", "A", 5.0)]), "en"))

    def test_old_holdings_say_so_in_the_subtitle(self):
        old = rh.build_html(fund([h("A", "A", 5.0)], as_of="2026-08-31"), "en")  # retrieved 2026-10-12
        self.assertIn("Holdings as of 2026-08-31 (42 days old)", old)
        zh = rh.build_html(fund([h("A", "A", 5.0)], as_of="2026-08-31"), "zh")
        self.assertIn("2026-08-31（距", zh)
        self.assertIn("42 天）", zh)
        fresh = rh.build_html(fund([h("A", "A", 5.0)], as_of="2026-10-09"), "en")
        self.assertIn("Holdings as of 2026-10-09 ·", fresh)
        self.assertNotIn("days old", fresh)
        self.assertNotIn("days old", rh.build_html(fund([h("A", "A", 5.0)], as_of="2026-08-31", retrieved_at=None), "en"))

    def test_unknown_as_of_is_shown_not_invented(self):
        html = rh.build_html(fund([h("A", "A", 5.0)], as_of=None), "en")
        self.assertIn("Holdings date not stated", html)

    def test_names_file_and_note(self):
        data = fund([h("NVDA", "NVIDIA Corp", 8.0)], note={"en": "Hypothetical example.", "zh": "虚构示例。"})
        html = rh.build_html(data, "en", names={"NVDA": {"zh": "英伟达"}})
        self.assertIn("NVIDIA Corp", html)
        self.assertTrue(html.count("Hypothetical example.") == 1 and "Source: Test file" in html)
        zh = rh.build_html(data, "zh", names={"NVDA": {"zh": "英伟达"}})
        self.assertIn("英偉達", zh)  # converted to Traditional Chinese like every other zh output
        self.assertIn("虛構示例", zh)

    def test_empty_ranking_is_an_error(self):
        with self.assertRaises(ValueError):
            rh.build_html(fund([h("A", "A", None)]), "en")

    def test_html_is_escaped(self):
        html = rh.build_html(fund([h("A<B", "Evil <script>alert(1)</script> Inc", 5.0)]), "en")
        self.assertNotIn("<script>alert", html)


class PricingDateCheck(unittest.TestCase):
    """live_check verifies the as-of date by comparing the file's own prices with official closes."""
    CLOSES = {"AAPL": 336.64, "NVDA": 229.28, "MU": 1029.0, "AMD": 150.0}   # official closes of Friday 2026-10-09

    def res(self, as_of="2026-10-09"):
        rows = [h(t, t, 10.0 - i, price=p) for i, (t, p) in enumerate(self.CLOSES.items())]
        return fund(rows, as_of=as_of)

    def series(self, sym):
        return {"2026-10-08": self.CLOSES[sym] * 1.02, "2026-10-09": self.CLOSES[sym]}   # newest close is Friday's

    def test_matching_prices_verify_the_date(self):
        problem, note = lc.pricing_date_problem(self.res(), self.series)
        self.assertIsNone(problem)
        self.assertIn("verified", note)

    def test_the_next_trading_day_stamp_is_caught_before_that_day_has_closed(self):
        """The bug this guards against: files stamped with the next trading day (Monday) were shown as holdings of that day."""
        problem, _ = lc.pricing_date_problem(self.res("2026-10-12"), self.series)
        self.assertIn("later than the newest official close", problem)

    def test_a_date_whose_close_exists_but_differs_is_caught(self):
        series = lambda sym: {"2026-10-09": self.CLOSES[sym], "2026-10-12": self.CLOSES[sym] * 1.04}
        problem, _ = lc.pricing_date_problem(self.res("2026-10-12"), series)
        self.assertIn("does not match the prices in the file", problem)

    def test_missing_closes_skip_the_check_instead_of_failing(self):
        problem, note = lc.pricing_date_problem(self.res(), lambda sym: None)
        self.assertIsNone(problem)
        self.assertIn("skipped", note)

    def test_only_us_tickers_with_prices_are_compared(self):
        rows = [h("000660 KS", "SK hynix", 9.0, price=1.0), h("", "Cash", 5.0, "cash", "c"), h("MU", "Micron", 4.0)]  # none usable
        problem, note = lc.pricing_date_problem(fund(rows), lambda sym: {"2026-10-09": 1.0})
        self.assertIsNone(problem)
        self.assertIn("skipped", note)


class LiveCheckLogic(unittest.TestCase):
    """The weekly live check must actually catch the ways an issuer page can break."""
    TODAY = dt.date(2026, 10, 12)

    def good(self, n=20, **kw):
        return fund([h(f"T{i}", f"Company {i}", 100.0 / n) for i in range(n)], **kw)

    def check(self, res, **kw):
        args = dict(min_holdings=10, max_age_days=10, needs_swaps=False, today=self.TODAY)
        args.update(kw)
        return lc.check_result(res, **args)

    def test_a_healthy_result_passes(self):
        self.assertEqual(self.check(self.good()), [])

    def test_partial_file_is_caught(self):
        self.assertTrue(any("only 3 holdings" in p for p in self.check(self.good(3))))

    def test_wrong_weights_are_caught(self):
        res = self.good()
        for x in res["holdings"]:
            x["weight"] = x["weight"] / 100  # a file that switched from percent to fractions
        self.assertTrue(any("add up to 1.0%" in p for p in self.check(res)))

    def test_missing_weights_are_caught(self):
        res = self.good()
        for x in res["holdings"][:10]:
            x["weight"] = None
        self.assertTrue(any("no weight" in p for p in self.check(res)))

    def test_stale_and_missing_dates_are_caught(self):
        self.assertTrue(any("days old" in p for p in self.check(self.good(as_of="2026-08-01"))))
        self.assertTrue(any("no as-of date" in p for p in self.check(self.good(as_of=None))))

    def test_swap_naming_change_is_caught(self):
        self.assertTrue(any("no swap rows" in p for p in self.check(self.good(), needs_swaps=True)))

    def test_everything_misclassified_is_caught(self):
        res = fund([h(f"T{i}", f"Company {i}", 5.0, kind="other") for i in range(20)])
        res["holdings"][0]["kind"] = "equity"  # one equity so the fallback to 'other' does not hide the problem
        self.assertEqual(self.check(res, min_holdings=10), [])
        res = fund([h(f"T{i}", f"Company {i}", 5.0, kind="cash") for i in range(20)])
        self.assertTrue(any("nothing left to rank" in p for p in self.check(res)))


class Examples(unittest.TestCase):
    def test_example_files_render(self):
        for name in ("etf_holdings_equity", "etf_holdings_swap"):
            data = json.loads((ROOT / "examples" / f"{name}.json").read_text(encoding="utf-8"))
            for lang in ("en", "zh"):
                html = rh.build_html(data, lang)
                self.assertIn("Past performance" if lang == "en" else "過往業績", html)
                saved = (ROOT / "examples" / f"{name}_{lang}.html").read_text(encoding="utf-8")
                self.assertEqual(html, saved, f"{name}_{lang}.html is stale; run render_holdings.py on the example")


if __name__ == "__main__":
    unittest.main()
