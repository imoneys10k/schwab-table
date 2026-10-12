"""Fetch an ETF's latest holdings from the issuer's own published file and normalise them to JSON.

Usage:
  python3 fetch_holdings.py QQQ -o data/qqq_holdings.json
  python3 fetch_holdings.py SPY VOO IVV QQQ QQQI NCLD DRAM -o data/        # several funds -> data/<SYMBOL>_holdings.json
  python3 fetch_holdings.py XLK --issuer ssga                              # force an issuer adapter
  python3 fetch_holdings.py MYETF --csv my_holdings.csv --name "My ETF"    # import a file you downloaded yourself
  python3 fetch_holdings.py QQQ --refresh                                  # ignore the 6-hour local cache

Sources (each is the issuer's own public holdings data; nothing is guessed or filled from memory)
  ssga      State Street SPDR funds (SPY, XLK, ...)   daily xlsx file
  ishares   iShares funds (IVV, IWM, AGG, ...)         latest-holdings.csv; product ids are listed in ISHARES_IDS
  vanguard  Vanguard equity ETFs (VOO, VTI, ...)      JSON behind the fund page (published monthly)
  neos      NEOS funds (QQQI, ...)                    CSV behind the fund page
  roundhill Roundhill funds (NCLD, DRAM, ...)         daily CSV covering all Roundhill funds
  tema      Tema ETFs (DISK, ...)                     daily CSV linked from the fund page
Invesco (QQQ, QQQM, ...) and Destiny (DXYZ) are not fetched: their terms of use forbid automated access to their websites.
Download the holdings yourself from the fund page and import them with --csv. The same goes for any other fund:
--csv takes columns name, ticker (optional) and weight; sector is optional.

Output JSON: {symbol, name, issuer, as_of, retrieved_at, source, source_url, weight_basis, holdings[], warnings[]}.
Each holding has ticker, name, weight (percent, null if unreported), sector, kind and id. kind is one of
equity, swap, cash, treasury, option, bond, other; swaps carry underlying_id so render_holdings.py can combine them
with the physical position. Weights are exactly as the issuer reports them.
"""
import argparse
import csv
import datetime as dt
import html as htmllib
import io
import json
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from fetch_prices import CACHE_DIR, UA, FetchError, http_get

CACHE_TTL = 6 * 3600
CACHE_VERSION = 3  # 3: bonds keep their base name for grouping; 2: NEOS / Roundhill as-of dates are the pricing day
STALE_DAYS = 10

# iShares serves a fund's holdings CSV from its numeric product id (the slug in the URL is ignored).
# Every id below was checked against the fund name in the CSV's first line.
ISHARES_IDS = {
    "IVV": 239726, "IWM": 239710, "AGG": 239458, "EFA": 239623, "EEM": 239637, "TLT": 239454, "LQD": 239566,
    "IJH": 239763, "IJR": 239774, "ITOT": 239724, "IEFA": 244049, "IEMG": 244050, "IWF": 239706, "IWD": 239708, "IWV": 239714,
}
# Funds whose issuer is known up front, so no probing is needed. Everything else is probed in ISSUERS order.
HINTS = {"VOO": "vanguard", "SPY": "ssga", "QQQI": "neos", "NCLD": "roundhill", "DRAM": "roundhill", "DISK": "tema",
         **{k: "ishares" for k in ISHARES_IDS}}
# Issuers whose terms of use forbid automated access. The tool does not fetch them; it tells the user how to import a file instead.
MANUAL = {
    "invesco": ("Invesco", "https://www.invesco.com/", {"QQQ", "QQQM", "QQQJ", "RSP"}),
    "destiny": ("Destiny", "https://destiny.xyz/tech100", {"DXYZ"}),
}
MANUAL_HINTS = {sym: key for key, (_, _, syms) in MANUAL.items() for sym in syms}
ISSUER_ORDER = ["ssga", "vanguard", "neos", "roundhill", "tema", "ishares"]
ISSUER_NAMES = {"ssga": "State Street (SPDR)", "ishares": "BlackRock iShares", "vanguard": "Vanguard",
                "neos": "NEOS", "roundhill": "Roundhill", "tema": "Tema ETFs", "csv": "User-provided file"}
KINDS = {"equity", "swap", "cash", "treasury", "option", "bond", "other"}


class NotThisIssuer(FetchError):
    """The issuer does not publish this fund (so the next adapter can be tried)."""


# ---- small helpers -------------------------------------------------------------------
def pct(value):
    """'8.07%', '8.07', '1,234.5', '-0.48%' -> float; blanks, '-' and 'NA' -> None."""
    s = str(value if value is not None else "").strip().replace(",", "").rstrip("%").strip()
    if s in ("", "-", "--", "NA", "N/A", "n/a"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def num(value):
    """'$1,029.00' or '1029.000000' -> float; blanks -> None."""
    try:
        return float(re.sub(r"[$,\s]", "", str(value if value is not None else "")))
    except ValueError:
        return None


def prev_weekday(d):
    d -= dt.timedelta(days=1)
    while d.weekday() >= 5:
        d -= dt.timedelta(days=1)
    return d


def clean(s):
    s = htmllib.unescape(str(s or "")).replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def holding(ticker, name, weight, sector=None, kind="equity", ident=None, underlying_id=None, price=None, base_name=None):
    sector = clean(sector)
    h = {"ticker": clean(ticker) if clean(ticker) not in ("-", "--") else "", "name": clean(name), "weight": weight,
         "sector": None if sector in ("", "-", "--") else sector, "kind": kind, "id": clean(ident) or None}
    if underlying_id:
        h["underlying_id"] = underlying_id
    if base_name:
        h["base_name"] = clean(base_name)  # the issuer's own name without what we add for readability (bond coupon and maturity)
    if price is not None:
        h["price"] = price  # the price the issuer used to value the position; lets live_check verify the as-of date
    return h


def fetch(url, accept="*/*", headers=None, tries=2, timeout=40):
    try:
        return http_get(url, accept=accept, timeout=timeout, tries=tries, headers=headers)
    except FetchError as e:
        raise FetchError(f"could not download {url}: {e}") from None


def fetch_bytes(url, headers=None, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            raise NotThisIssuer(f"{url} returned HTTP {e.code}") from None
        raise FetchError(f"could not download {url}: HTTP {e.code}") from None
    except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
        raise FetchError(f"could not download {url}: {e}") from None


def parse_date(s):
    s = clean(s)
    m = re.match(r"(\d{4}-\d{2}-\d{2})(?:T|$)", s)  # ISO date, optionally followed by a time
    if m:
        s = m.group(1)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%b %d, %Y", "%B %d, %Y", "%Y%m%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def result(symbol, issuer, rows, as_of, source, url, name=None, basis="% of net assets", warnings=None):
    return {"symbol": symbol, "name": clean(name) or None, "issuer": ISSUER_NAMES.get(issuer, issuer), "issuer_key": issuer,
            "as_of": as_of.isoformat() if as_of else None, "source": source, "source_url": url, "weight_basis": basis,
            "holdings": rows, "warnings": list(warnings or [])}


# ---- SSGA -------------------------------------------------------------------------
def read_xlsx_rows(blob):
    """Rows of the first worksheet as {column letter: text}. Enough of xlsx for SSGA's holdings file."""
    z = zipfile.ZipFile(io.BytesIO(blob))
    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        shared = [htmllib.unescape(re.sub(r"<[^>]+>", "", m)) for m in re.findall(r"<si>(.*?)</si>", z.read("xl/sharedStrings.xml").decode("utf-8"), re.S)]
    sheet = sorted(n for n in z.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n))[0]
    out = []
    for r in re.findall(r"<row [^>]*>(.*?)</row>", z.read(sheet).decode("utf-8"), re.S):
        cells = {}
        for col, attrs, inner in re.findall(r'<c r="([A-Z]+)\d+"([^>]*?)(?:/>|>(.*?)</c>)', r, re.S):
            v = re.search(r"<v>(.*?)</v>", inner or "", re.S)
            if v:
                cells[col] = shared[int(v.group(1))] if 't="s"' in attrs else v.group(1)
            else:
                t = re.search(r"<t[^>]*>(.*?)</t>", inner or "", re.S)
                if t:
                    cells[col] = htmllib.unescape(t.group(1))
        if cells:
            out.append(cells)
    return out


def parse_ssga(symbol, blob, url):
    rows = read_xlsx_rows(blob)
    meta = {clean(r.get("A")).rstrip(":"): clean(r.get("B")) for r in rows[:6] if "B" in r}
    head = next((i for i, r in enumerate(rows) if clean(r.get("A")) == "Name" and clean(r.get("E")) == "Weight"), None)
    if head is None:
        raise FetchError("SSGA file has no Name/Weight header row; the layout changed")
    cols = {clean(v): k for k, v in rows[head].items()}
    out = []
    for r in rows[head + 1:]:
        w = pct(r.get(cols["Weight"]))
        name = clean(r.get(cols["Name"]))
        if w is None or not name:
            if out:
                break  # the disclaimer block starts after the last holding
            continue
        ticker = clean(r.get(cols["Ticker"]))
        kind = "cash" if re.search(r"\b(US DOLLAR|CASH|CURRENCY)\b", name.upper()) and not ticker.strip("-") else "equity"
        out.append(holding(ticker, name, w, r.get(cols.get("Sector", "")), kind, r.get(cols.get("Identifier", ""))))
    as_of = parse_date(re.sub(r"^As of\s*", "", meta.get("Holdings", ""), flags=re.I))
    if (meta.get("Ticker Symbol") or symbol).upper() != symbol:
        raise FetchError(f"SSGA file is for {meta.get('Ticker Symbol')}, not {symbol}")
    return result(symbol, "ssga", out, as_of, "State Street Investment Management (issuer holdings file)", url, meta.get("Fund Name"))


def fetch_ssga(symbol, **_):
    url = f"https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-{symbol.lower()}.xlsx"
    return parse_ssga(symbol, fetch_bytes(url), url)


# ---- iShares ----------------------------------------------------------------------
ISHARES_KINDS = {"equity": "equity", "money market": "cash", "cash": "cash", "cash collateral and margins": "cash", "futures": "other",
                 "fixed income": "bond"}


def parse_ishares(symbol, text, url):
    head, _, body = text.lstrip("\ufeff").partition("\n\n")
    lines = head.splitlines()
    name = clean(lines[0].strip('"')) if lines else None
    m = re.search(r"Fund Holdings as of,\s*\"?([^\"\n]+)", head)
    as_of = parse_date(m.group(1)) if m else None
    body = body.strip()
    # equity funds start with "Ticker,Name,..."; bond funds have no ticker column and start with "Name,..."
    if not (body.startswith("Ticker,") or body.startswith("Name,")):
        raise FetchError("iShares file has no holdings table; the layout changed")
    out = []
    for r in csv.DictReader(io.StringIO(body)):
        if not r.get("Name") or pct(r.get("Weight (%)")) is None:
            continue
        kind = ISHARES_KINDS.get(clean(r.get("Asset Class")).lower(), "other")
        label = r["Name"]
        if kind == "bond":  # many bonds share a generic name such as "TREASURY NOTE": add coupon and maturity to tell them apart
            coupon, maturity = pct(r.get("Coupon (%)")), clean(r.get("Maturity"))
            label = clean(label) + (f" {coupon:g}%" if coupon is not None else "") + (f" {maturity}" if maturity not in ("", "-") else "")
        out.append(holding(r.get("Ticker"), label, pct(r["Weight (%)"]), r.get("Sector"), kind, r.get("ISIN") or r.get("CUSIP"),
                           base_name=r["Name"] if kind == "bond" else None))
    return result(symbol, "ishares", out, as_of, "BlackRock iShares (issuer holdings file)", url, name)


def fetch_ishares(symbol, **_):
    if symbol not in ISHARES_IDS:
        raise NotThisIssuer(f"{symbol} is not in the verified iShares product-id list")
    url = f"https://www.ishares.com/us/products/{ISHARES_IDS[symbol]}/x/latest-holdings.csv"
    return parse_ishares(symbol, fetch(url, accept="text/csv,*/*"), url)


# ---- Vanguard ---------------------------------------------------------------------
def parse_vanguard(symbol, pages, url):
    out, as_of = [], None
    for p in pages:
        as_of = as_of or parse_date(p.get("asOfDate"))
        for e in (p.get("fund") or {}).get("entity") or []:
            out.append(holding(e.get("ticker"), e.get("longName") or e.get("shortName"), pct(e.get("percentWeight")), None, "equity",
                               e.get("cusip") or e.get("isin")))
    return result(symbol, "vanguard", out, as_of, "Vanguard (issuer holdings data, published monthly)", url)


def fetch_vanguard(symbol, **_):
    base = f"https://investor.vanguard.com/vmf/api/{symbol}/portfolio-holding/stock.json"
    pages, start = [], 1
    while True:
        page = json.loads(fetch(f"{base}?start={start}&count=500", accept="application/json"))
        entities = (page.get("fund") or {}).get("entity") or []
        if not entities:
            break
        pages.append(page)
        start += 500
        if start > page.get("size", 0) or start > 5000:
            break
    if not pages:
        raise NotThisIssuer(f"Vanguard publishes no equity holdings for {symbol} (bond and multi-asset funds are not supported; use --csv)")
    return parse_vanguard(symbol, pages, base)


# ---- NEOS and Roundhill (same CSV layout) ------------------------------------------------
def classify_neos_like(ticker, name, flag, cusip):
    u, t = name.upper(), ticker.strip()
    if " TRS " in f" {t} " or "SWAP" in u:
        return "swap"
    if flag.strip().upper() == "Y" or u.startswith("CASH") or str(cusip).upper().startswith("CASH"):
        return "cash"
    if re.search(r"TREASURY (BILL|NOTE|BOND)|\bT-BILL\b", u):
        return "treasury"
    if re.fullmatch(r"[A-Z]+\s+(US\s+)?\d{6}[CP]\d+", t) or re.search(r"\b\d\d/\d\d/\d\d [CP]\d", name):
        return "option"
    return "equity"


def swap_name(name):
    n = re.sub(r"[-\s]*SWAP[-\s]*(NM|NMRA|GOLD|GS)?[-\s]*L?\s*$", "", name, flags=re.I)
    n = re.sub(r"\s*-?SWAP-[A-Z]+-[A-Z]\s*$", "", n)
    return clean(n)


def parse_neos_like(symbol, issuer, text, url, source, valuation_date=None):
    """NEOS and Roundhill files. Their 'Date' column is the next trading day (the day the basket takes effect); the prices in the
    file are the previous close. Checked against official closes: Roundhill's 10-09 file holds the 10-09 closes and is stamped 10-12.
    So the as-of date is the file's own date when the URL carries one (Roundhill), else the weekday before the stamp (NEOS)."""
    rows = [r for r in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))) if clean(r.get("Account")).upper() == symbol]
    if not rows:
        raise NotThisIssuer(f"{ISSUER_NAMES[issuer]} has no fund {symbol} in its holdings file")
    out, dates = [], []
    for r in rows:
        ticker, name, cusip = clean(r.get("StockTicker")), clean(r.get("SecurityName")), clean(r.get("Cusip") or r.get("CUSIP"))
        kind = classify_neos_like(ticker, name, r.get("MoneyMarketFlag") or "", cusip)
        under = ticker.split()[0] if kind == "swap" else None
        out.append(holding("" if kind == "swap" else ticker, swap_name(name) if kind == "swap" else name, pct(r.get("Weightings")),
                           None, kind, cusip if kind != "swap" else ticker, under, price=num(r.get("Price")) if kind == "equity" else None))
        if parse_date(r.get("Date")):
            dates.append(parse_date(r["Date"]))
    stamped = max(dates) if dates else None
    as_of = valuation_date or (prev_weekday(stamped) if stamped else None)
    res = result(symbol, issuer, out, as_of, source, url)
    if stamped and as_of != stamped:
        res["issuer_date"] = stamped.isoformat()
    if issuer == "roundhill":
        # Roundhill's own top-holdings script adds swap and share lines of one company (DRAM: by the first four letters of the name,
        # so SK hynix and Samsung's second listings are included; NCLD: by CUSIP). The renderer follows by merging lines with equal names.
        res["merge_by_name"] = True
    return res


def fetch_neos(symbol, **_):
    url = f"https://neosfunds.com/wp-admin/admin-ajax.php?action=download_holdings_csv&ticker={symbol}"
    text = fetch(url, accept="text/csv,*/*")
    if not text.startswith("Date,"):
        raise NotThisIssuer(f"NEOS does not list {symbol} ({text.strip()[:60] or 'empty reply'})")
    return parse_neos_like(symbol, "neos", text, url, "NEOS Funds (issuer holdings file)")


def fetch_roundhill(symbol, now=None, **_):
    today = (now or dt.datetime.now(dt.timezone.utc)).date()
    last = None
    for back in range(0, 8):
        d = today - dt.timedelta(days=back)
        if d.weekday() >= 5:
            continue
        url = f"https://www.roundhillinvestments.com/assets/data/FilepointRoundhill.40RU.RU_Holdings_{d.strftime('%m%d%Y')}.csv"
        try:
            text = fetch(url, accept="text/csv,*/*", tries=1)
        except FetchError as e:
            last = e
            continue
        if text.lstrip("﻿").startswith("Date,"):  # a missing day redirects to an HTML 404 page
            return parse_neos_like(symbol, "roundhill", text, url, "Roundhill Investments (issuer holdings file, all funds)", valuation_date=d)
    raise FetchError(f"no Roundhill holdings file found for the last 8 days{f' ({last})' if last else ''}")


# ---- Tema ETFs -----------------------------------------------------------------------------------
def parse_tema(symbol, text, url):
    """Tema's CSV: holdings_date, ticker, cusip, proper_name, shares, market_value, percent_of_nav (a fraction), is_cash, country, sector."""
    out, dates = [], []
    for r in csv.DictReader(io.StringIO(text.lstrip("\ufeff"))):
        name, ticker = clean(r.get("proper_name")), clean(r.get("ticker"))
        w = pct(r.get("percent_of_nav"))
        if not name:
            continue
        if clean(r.get("is_cash")) == "1":
            kind = "cash"
        elif "-TRS-" in ticker.upper() or "SWAP" in name.upper():
            kind = "swap"
        elif re.search(r"TREASURY (BILL|NOTE|BOND)", name.upper()):
            kind = "treasury"
        else:
            kind = "equity"
        under = re.split(r"-TRS-", ticker, flags=re.I)[0] if kind == "swap" else None
        shares, value = num(r.get("shares")), num(r.get("market_value"))
        price = round(value / shares, 4) if kind == "equity" and shares and value else None
        out.append(holding("" if kind in ("swap", "cash") else ticker, swap_name(name) if kind == "swap" else name,
                           None if w is None else round(w * 100, 4), r.get("sector"), kind,
                           ticker if kind == "swap" else (clean(r.get("cusip")) or ticker), under, price=price))
        if parse_date(r.get("holdings_date")):
            dates.append(parse_date(r["holdings_date"]))
    if not out:
        raise NotThisIssuer(f"Tema's file for {symbol} has no holdings")
    return result(symbol, "tema", out, max(dates) if dates else None, "Tema ETFs (issuer holdings file)", url)


def fetch_tema(symbol, now=None, **_):
    today = (now or dt.datetime.now(dt.timezone.utc)).date()
    for back in range(0, 8):
        d = today - dt.timedelta(days=back)
        if d.weekday() >= 5:
            continue
        url = f"https://temaetfs.com/hubfs/Website/Holdings/{symbol}-holdings-{d.strftime('%m%d%Y')}.csv"
        try:
            text = fetch(url, accept="text/csv,*/*", tries=1)
        except FetchError:
            continue  # not published for that day (or not a Tema fund)
        if text.lstrip("\ufeff").startswith("holdings_date,"):
            return parse_tema(symbol, text, url)
    raise NotThisIssuer(f"Tema has no holdings file for {symbol} in the last 8 days")


# ---- user CSV ----------------------------------------------------------------------------------
NAME_COLS = ("name", "security name", "holding", "holding name", "issuer", "description", "名称", "名稱", "证券名称")
TICKER_COLS = ("ticker", "symbol", "stock ticker", "holding ticker", "identifier", "代码", "代碼")
WEIGHT_COLS = ("weight", "weight (%)", "weighting", "weightings", "% of net assets", "% of fund", "% weight", "percent", "占比", "權重", "权重")
SECTOR_COLS = ("sector", "industry", "行业", "行業")


def parse_user_csv(symbol, text, path, name=None):
    lines = text.lstrip("﻿").splitlines()
    start = next((i for i, ln in enumerate(lines) if any(c in ln.lower() for c in ("weight", "占比", "權重", "权重", "% of"))), None)
    if start is None:
        raise FetchError(f"{path}: no header row with a weight column (expected one of: {', '.join(WEIGHT_COLS[:5])}...)")
    reader = csv.DictReader(io.StringIO("\n".join(lines[start:])))
    low = {clean(k).lower(): k for k in reader.fieldnames or [] if k}

    def pick(options):
        return next((low[o] for o in options if o in low), None)

    wc, nc, tc, sc = pick(WEIGHT_COLS), pick(NAME_COLS), pick(TICKER_COLS), pick(SECTOR_COLS)
    if not wc or not (nc or tc):
        raise FetchError(f"{path}: need a weight column and a name or ticker column; found {list(low)}")
    out = []
    for r in reader:
        w = pct(r.get(wc))
        label = clean(r.get(nc)) if nc else ""
        tick = clean(r.get(tc)) if tc else ""
        if w is None or not (label or tick):
            continue
        out.append(holding(tick, label or tick, w, r.get(sc) if sc else None))
    if not out:
        raise FetchError(f"{path}: no holdings rows with a numeric weight")
    return result(symbol, "csv", out, None, f"User-provided data ({Path(path).name})", str(path), name,
                  warnings=["as-of date unknown: add it with --as-of YYYY-MM-DD"])


# ---- orchestration -----------------------------------------------------------------------------------
ADAPTERS = {"ssga": fetch_ssga, "ishares": fetch_ishares, "vanguard": fetch_vanguard,
            "neos": fetch_neos, "roundhill": fetch_roundhill, "tema": fetch_tema}


def manual_message(symbol, key):
    name, site, _ = MANUAL[key]
    return (f"{name}'s terms of use forbid automated access to its website, so this tool does not fetch {symbol}. Download the holdings from the fund "
            f"page at {site} and import the file: python3 fetch_holdings.py {symbol} --csv FILE --name \"Fund name\" --as-of YYYY-MM-DD")


def fund_name(symbol):
    """Fund name from Nasdaq's quote endpoint, for issuers whose files carry none. Best effort only."""
    for cls in ("etf", "stocks"):
        try:
            d = json.loads(http_get(f"https://api.nasdaq.com/api/quote/{symbol}/info?assetclass={cls}", tries=1, timeout=15)).get("data")
            if d and d.get("companyName"):
                return clean(d["companyName"])
        except (FetchError, ValueError):
            continue
    return None


def validate(res):
    rows = res["holdings"]
    if not rows:
        raise FetchError(f"{res['symbol']}: the {res['issuer']} file contained no holdings")
    for h in rows:
        if h["kind"] not in KINDS:
            raise FetchError(f"internal error: unknown holding kind {h['kind']!r}")
    weights = [h["weight"] for h in rows if h["weight"] is not None]
    if not weights:
        raise FetchError(f"{res['symbol']}: no weights in the {res['issuer']} file")
    total = sum(weights)
    if not 90 <= total <= 110:
        res["warnings"].append(f"listed weights add up to {total:.1f}%, not about 100%; the file may be partial")
    missing = len(rows) - len(weights)
    if missing:
        res["warnings"].append(f"{missing} holding(s) have no reported weight (shown as NA, never as 0)")


def finish(res, now):
    """Common checks, name lookup and staleness warning."""
    validate(res)
    if res["as_of"]:
        age = (now.date() - dt.date.fromisoformat(res["as_of"])).days
        if age > STALE_DAYS:
            res["warnings"].append(f"holdings are as of {res['as_of']}, {age} days before retrieval; holdings change, so check for a newer file")
    if not res["name"]:
        res["name"] = fund_name(res["symbol"])
    res["retrieved_at"] = now.replace(microsecond=0).isoformat()
    return res


def cache_file(symbol, issuer):
    return CACHE_DIR / f"holdings_v{CACHE_VERSION}_{symbol}_{issuer or 'auto'}.json"


def get_holdings(symbol, issuer=None, refresh=False, now=None):
    symbol = symbol.strip().upper()
    now = now or dt.datetime.now(dt.timezone.utc)
    manual = issuer if issuer in MANUAL else (MANUAL_HINTS.get(symbol) if not issuer else None)
    if manual:
        raise FetchError(manual_message(symbol, manual))
    cf = cache_file(symbol, issuer)
    if not refresh:
        try:
            cached = json.loads(cf.read_text(encoding="utf-8"))
            if time.time() - cached["saved_at"] < CACHE_TTL:
                return cached["data"]
        except (OSError, ValueError, KeyError):
            pass
    if issuer:
        if issuer not in ADAPTERS:
            raise FetchError(f"unknown issuer {issuer!r}; choose from {', '.join(ADAPTERS)}")
        order = [issuer]
    else:
        hinted = HINTS.get(symbol)
        order = [hinted] if hinted else [i for i in ISSUER_ORDER]
    errors = []
    for key in order:
        try:
            res = finish(ADAPTERS[key](symbol, now=now), now)
            break
        except NotThisIssuer as e:
            errors.append(f"{key}: {e}")
        except FetchError as e:
            if issuer or HINTS.get(symbol):
                raise
            errors.append(f"{key}: {e}")
    else:
        raise FetchError(f"no issuer adapter found it ({'; '.join(errors)}). Download the issuer's holdings CSV and use --csv.")
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps({"saved_at": time.time(), "data": res}), encoding="utf-8")
    except OSError:
        pass
    return res


def out_path(symbol, target, many):
    if target is None:
        return Path("data") / f"{symbol}_holdings.json"
    p = Path(target)
    if many or target.endswith(("/", "\\")) or p.is_dir():
        return p / f"{symbol}_holdings.json"
    return p


def main():
    ap = argparse.ArgumentParser(description="Fetch ETF holdings from the issuer and write normalised JSON.")
    ap.add_argument("symbols", nargs="+", help="ETF tickers, e.g. QQQ SPY VOO")
    ap.add_argument("-o", "--out", help="output file (one symbol) or directory (several); default data/<SYMBOL>_holdings.json")
    ap.add_argument("--issuer", choices=sorted(ADAPTERS), help="force one issuer adapter instead of the automatic choice")
    ap.add_argument("--csv", help="import a holdings CSV you downloaded yourself (one symbol only)")
    ap.add_argument("--name", help="fund name to print on the chart (with --csv, or to override)")
    ap.add_argument("--as-of", help="as-of date for --csv data, YYYY-MM-DD")
    ap.add_argument("--refresh", action="store_true", help="ignore the 6-hour local cache")
    a = ap.parse_args()
    if a.csv and len(a.symbols) != 1:
        sys.exit("error: --csv takes exactly one symbol")
    failed = 0
    for sym in a.symbols:
        sym = sym.upper()
        try:
            now = dt.datetime.now(dt.timezone.utc)
            if a.csv:
                try:
                    text = Path(a.csv).read_text(encoding="utf-8-sig")
                except OSError as e:
                    sys.exit(f"error: cannot read {a.csv}: {e}")
                res = parse_user_csv(sym, text, a.csv, a.name)
                if a.as_of:
                    try:
                        res["as_of"] = dt.date.fromisoformat(a.as_of).isoformat()
                        res["warnings"] = [w for w in res["warnings"] if not w.startswith("as-of date unknown")]
                    except ValueError:
                        sys.exit("error: --as-of must be YYYY-MM-DD")
                res = finish(res, now)
            else:
                res = get_holdings(sym, a.issuer, a.refresh, now)
            if a.name:
                res["name"] = a.name
        except FetchError as e:
            print(f"error: {sym}: {e}", file=sys.stderr)
            failed += 1
            continue
        path = out_path(sym, a.out, len(a.symbols) > 1)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{sym}: {len(res['holdings'])} holdings | {res['issuer']} | as of {res['as_of'] or 'unknown'} -> {path}")
        for w in res["warnings"]:
            print(f"  warning: {w}", file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
