"""Generate examples/etf_holdings_*.json: SYNTHETIC ETF holdings for fictional companies (same schema as fetch_holdings.py).

Not real funds or weights. Run from anywhere: python3 examples/make_etf_holdings.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTE = {"en": "Hypothetical example with fictional companies; not a real fund.", "zh": "虚构示例，公司均为虚构，并非真实基金。"}
COMPANIES = [  # ticker, name, sector
    ("ACRB", "Acme Robotics Inc", "Industrials"), ("STRK", "Stark Aerospace Corp", "Industrials"), ("HOOL", "Hooli Cloud Inc", "Technology"),
    ("INSY", "Initech Systems Inc", "Technology"), ("UMBB", "Umbrella Biotech Inc", "Health Care"), ("CYDN", "Cyberdyne Labs Inc", "Technology"),
    ("GLBXA", "Globex Energy Corp Class A", "Energy"), ("GLBXB", "Globex Energy Corp Class B", "Energy"), ("WAYN", "Wayne Industries Inc", "Industrials"),
    ("SOYL", "Soylent Foods Corp", "Consumer Staples"), ("VAND", "Vandelay Imports Inc", "Consumer Discretionary"), ("PIED", "Pied Piper Inc", "Technology"),
    ("DUND", "Dunder Paper Co", "Materials"), ("MASS", "Massive Dynamic Inc", "Health Care"), ("OSCP", "Oscorp Therapeutics", "Health Care"),
    ("TYRL", "Tyrell Devices Corp", "Technology"), ("WONK", "Wonka Confections Inc", "Consumer Staples"), ("BLTH", "Bluth Homes Inc", "Real Estate"),
    ("STRK2", "Sterling Archer Media", "Communication Services"), ("NAKA", "Nakatomi Trading Corp", "Financials"), ("GEKK", "Gekko Capital Group", "Financials"),
    ("PRSC", "Prestige Cruises Ltd", "Consumer Discretionary"), ("WYLD", "Wyld Stallyns Audio", "Consumer Discretionary"), ("KRUS", "Krusty Krab Holdings", "Consumer Discretionary"),
]


def holding(ticker, name, weight, sector=None, kind="equity", ident=None, **extra):
    return {"ticker": ticker, "name": name, "weight": weight, "sector": sector, "kind": kind, "id": ident or ticker + "0001", **extra}


def fund(symbol, name, rows, source):
    return {"symbol": symbol, "name": name, "issuer": "Synthetic sample", "issuer_key": "sample", "as_of": "2026-10-02",
            "source": source, "source_url": "", "weight_basis": "% of net assets", "holdings": rows, "warnings": [],
            "retrieved_at": "2026-10-02T00:00:00+00:00", "note": NOTE}


def equity_fund():
    top = [9.84, 7.91, 6.42, 5.57, 4.88, 4.43, 3.92, 3.51, 3.14, 2.86, 2.62, 2.41, 2.23]
    cash = 0.35
    rest_n = len(COMPANIES) - len(top)
    raw = [0.9 ** i for i in range(rest_n)]
    scale = (100 - cash - sum(top)) / sum(raw)
    weights = top + [round(w * scale, 2) for w in raw]
    weights[-1] = round(weights[-1] + (100 - cash - sum(weights)), 2)
    rows = [holding(t, n, w, sec) for (t, n, sec), w in zip(COMPANIES, weights)]
    rows.append(holding("", "Cash & equivalents", cash, None, "cash", "CASHUSD"))
    return fund("EXGR", "Example Growth ETF", rows, "Synthetic sample data (not a real fund)")


def swap_fund():
    phys = [("ACRB", "Acme Robotics Inc", 8.0), ("STRK", "Stark Aerospace Corp", 6.0), ("HOOL", "Hooli Cloud Inc", 5.0),
            ("INSY", "Initech Systems Inc", 4.0), ("UMBB", "Umbrella Biotech Inc", 3.0), ("CYDN", "Cyberdyne Labs Inc", 2.0)]
    rows = [holding(t, n, w, None, "equity", t + "0001") for t, n, w in phys]
    rows += [holding("", "Acme Robotics Inc", 11.0, None, "swap", "ACRB0001 TRS 1", underlying_id="ACRB0001"),
             holding("", "Acme Robotics Inc", 9.0, None, "swap", "ACRB0001 TRS 2", underlying_id="ACRB0001"),
             holding("", "Stark Aerospace Corp", 8.0, None, "swap", "STRK0001 TRS 1", underlying_id="STRK0001"),
             holding("", "Stark Aerospace Corp", 6.0, None, "swap", "STRK0001 TRS 2", underlying_id="STRK0001"),
             holding("", "Wayne Industries Inc", 12.0, None, "swap", "WAYN0001 TRS 1", underlying_id="WAYN0001")]
    rows += [holding("", "United States Treasury Bill 12/03/2026", 38.0, None, "treasury", "TBILL1"),
             holding("", "Example Government Money Market Fund", 6.0, None, "cash", "MMF0001"),
             holding("", "Cash & Other", -18.0, None, "cash", "Cash&Other")]
    return fund("EXSW", "Example Swap-Enhanced ETF", rows, "Synthetic sample data (not a real fund)")


if __name__ == "__main__":
    for name, data in (("etf_holdings_equity.json", equity_fund()), ("etf_holdings_swap.json", swap_fund())):
        (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("wrote", name, round(sum(h["weight"] for h in data["holdings"]), 2))
