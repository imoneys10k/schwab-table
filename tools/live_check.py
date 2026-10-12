"""Live health check for the ETF holdings adapters: fetch one real fund per issuer and sanity-check what comes back.

The issuers' endpoints are public pages and files, not documented APIs, so any of them can change. This script is run
weekly by .github/workflows/live-check.yml (and on demand) so a break is noticed before a user hits it.

Usage:
  python3 tools/live_check.py                 # every issuer 
  python3 tools/live_check.py --only ssga,vanguard
  python3 tools/live_check.py --skip tema
Exit code 1 if any check fails. Nothing is written except the local response cache.
"""
import argparse
import datetime as dt
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import fetch_holdings as fh  # noqa: E402
import fetch_prices as fp  # noqa: E402
import render_holdings as rh  # noqa: E402

# issuer key -> (fund, minimum holdings, maximum age of the as-of date in days, must contain swaps)
# VERIFY_DATE: issuers whose files carry the price they used; the as-of date is checked against Nasdaq's official closes.
VERIFY_DATE = {"neos", "roundhill", "tema"}
CASES = {
    "ssga": ("SPY", 400, 10, False),
    "ishares": ("IVV", 400, 10, False),
    "ishares-bond": ("TLT", 20, 10, False),
    "vanguard": ("VOO", 400, 50, False),      # Vanguard publishes monthly
    "neos": ("QQQI", 90, 10, False),
    "roundhill": ("DRAM", 10, 10, True),
    "tema": ("DISK", 10, 10, True),
}


def check_result(res, min_holdings, max_age_days, needs_swaps, today=None):
    """Return a list of problems (empty when the result looks right)."""
    today = today or dt.datetime.now(dt.timezone.utc).date()
    problems = []
    rows = res.get("holdings") or []
    if len(rows) < min_holdings:
        problems.append(f"only {len(rows)} holdings (expected at least {min_holdings})")
    weights = [h["weight"] for h in rows if h.get("weight") is not None]
    if rows and len(weights) < 0.9 * len(rows):
        problems.append(f"{len(rows) - len(weights)} of {len(rows)} holdings have no weight")
    total = sum(weights)
    if not 80 <= total <= 120:
        problems.append(f"weights add up to {total:.1f}%")
    if not res.get("as_of"):
        problems.append("no as-of date")
    else:
        age = (today - dt.date.fromisoformat(res["as_of"])).days
        if age > max_age_days:
            problems.append(f"as-of date {res['as_of']} is {age} days old (limit {max_age_days})")
        if age < -1:
            problems.append(f"as-of date {res['as_of']} is in the future")
    if needs_swaps and not any(h["kind"] == "swap" for h in rows):
        problems.append("no swap rows found; the issuer's swap naming may have changed")
    if any(not h["name"] for h in rows):
        problems.append("some holdings have no name")
    try:
        ranked, _, _ = rh.build_rows(res)
        if not ranked:
            problems.append("nothing left to rank after classification")
        elif ranked[0]["total"] <= 0:
            problems.append("top holding has no positive weight")
        for lang in ("en", "zh"):
            rh.build_html(res, lang)
    except Exception as e:  # a render failure is a failed check, not a crash
        problems.append(f"render failed: {e}")
    return problems


def official_closes(symbol):
    """Nasdaq official closes as {iso date: close} for roughly the last month, or None when they cannot be looked up."""
    today = dt.datetime.now(dt.timezone.utc).date()
    try:
        entry, _ = fp.get_series(symbol, today - dt.timedelta(days=35), today, refresh=False)
    except Exception:
        return None
    return {p[0]: p[1] for p in entry["points"]}


def pricing_date_problem(res, series_fn=official_closes):
    """Compare the prices inside the file with official closes. Returns (problem or None, note).
    Issuers stamp files with different dates (NEOS and Roundhill use the next trading day), so the as-of date is only trusted
    when the file's own prices equal the official close of that day for most of the biggest US-listed holdings. A date later
    than the newest official close cannot be the pricing day at all."""
    if not res.get("as_of"):
        return None, "no as-of date to verify"
    as_of = dt.date.fromisoformat(res["as_of"])
    picks = [h for h in sorted(res["holdings"], key=lambda x: -(x["weight"] or 0))
             if h["kind"] == "equity" and h.get("price") and re.fullmatch(r"[A-Z]{1,5}", h["ticker"] or "")][:4]
    checked = matched = future = 0
    for h in picks:
        series = series_fn(h["ticker"])
        if not series:
            continue
        close = series.get(as_of.isoformat())
        if close:
            checked += 1
            matched += abs(h["price"] - close) <= 0.005 * close
        elif as_of.isoformat() > max(series):
            future += 1
    if future >= 2:
        return (f"as-of date {as_of} is later than the newest official close, so the file's prices cannot be from that day; "
                f"the issuer's date convention may have changed"), ""
    if checked < 2:
        return None, "date check skipped (official closes not available)"
    if matched * 2 < checked:
        return (f"as-of date {as_of} does not match the prices in the file: only {matched} of {checked} large holdings equal "
                f"their official close on that day; the issuer's date convention may have changed"), ""
    return None, f"as-of date verified against official closes ({matched}/{checked})"


def main():
    ap = argparse.ArgumentParser(description="Fetch one real fund per issuer and sanity-check the result.")
    ap.add_argument("--only", help="comma-separated case names to run (default: all)")
    ap.add_argument("--skip", help="comma-separated case names to skip")
    a = ap.parse_args()
    names = list(CASES)
    if a.only:
        names = [n.strip() for n in a.only.split(",")]
        unknown = [n for n in names if n not in CASES]
        if unknown:
            sys.exit(f"error: unknown case(s) {', '.join(unknown)}; choose from {', '.join(CASES)}")
    if a.skip:
        names = [n for n in names if n not in {s.strip() for s in a.skip.split(",")}]
    failed = 0
    for name in names:
        symbol, min_n, max_age, swaps = CASES[name]
        issuer = name.split("-")[0]
        started = time.time()
        try:
            res = fh.get_holdings(symbol, issuer=issuer, refresh=True)
            problems = check_result(res, min_n, max_age, swaps)
            date_note = ""
            if issuer in VERIFY_DATE:
                date_problem, date_note = pricing_date_problem(res)
                if date_problem:
                    problems.append(date_problem)
        except fh.FetchError as e:
            res, problems, date_note = None, [f"fetch failed: {e}"], ""
        status = "ok  " if not problems else "FAIL"
        detail = (f"{len(res['holdings'])} holdings, as of {res['as_of']}" + (f"; {date_note}" if date_note else "")) if res else ""
        print(f"{status} {name:13} {symbol:5} {detail} ({time.time() - started:.1f}s)")
        for p in problems:
            print(f"       - {p}")
        failed += bool(problems)
    print(f"\n{len(names) - failed}/{len(names)} issuer checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
