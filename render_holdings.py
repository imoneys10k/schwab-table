"""Render an ETF's top-N holdings (bars + table, EN + ZH) from fetch_holdings.py output.

Usage: python3 render_holdings.py holdings.json OUT_PREFIX [--top 13] [--mode exposure|lines] [--merge-classes]
                                  [--names names.json] [--langs en,zh] [--no-png] [--pdf] [--scale 2] [--theme light|dark]

Modes
  exposure (default)  Rank by economic exposure: a swap on a stock is added to the physical position in the same stock
                      (matched by CUSIP/SEDOL), and cash, money-market funds, Treasury bills and options are left out of the
                      ranking and reported on their own line. This is the view Roundhill and similar issuers call "top holdings".
  lines               Rank every line exactly as the issuer lists it, swaps and T-bills included, with no merging.
--by                 holding (default), name or sector: add the lines of one issuer name, or one sector, together and rank the groups.
                      A fund with thousands of lines (a bond or small-cap index fund) says little in a top-13 of single lines.
--merge-classes       Add share classes of one company together (GOOGL + GOOG). Off by default.
--names               JSON {"NVDA": {"zh": "英伟达"}} to show a local-language name beside the ticker in that language.
An optional "note": {"en": ..., "zh": ...} key in the data file is printed at the start of the footnote (the examples use it to mark hypothetical funds).
Weights are shown exactly as the issuer reports them (percent of net assets unless the file says otherwise);
missing weights stay NA and never count as zero.
"""
import argparse
import datetime as dt
import json
import re
import sys
from html import escape
from pathlib import Path

from fonts import font_face_css
from localization import traditional_html
from render_common import THEMES, render_files

FONT = ('"Inter","Helvetica Neue",Helvetica,Arial,"Noto Sans CJK TC","Source Han Sans TC","PingFang TC","Microsoft JhengHei",sans-serif')
MAX_TOP = 50
STALE_DAYS = 10  # same threshold as fetch_holdings.py; older holdings get an age tag in the subtitle
EXCLUDED_KINDS = ("cash", "treasury", "option")
GROUPS = ("holding", "name", "sector")
DIFFUSE_SHARE = 15.0   # % of the listed weights; below this a top-N of single lines says little about concentration
DIFFUSE_LINES = 100

S = {
    "en": {
        "title": "{name} ({sym}) · Top {n} {unit_title}", "title_sym": "{sym} · Top {n} {unit_title}",
        "unit_title": {"holding": "Holdings", "name": "Names", "sector": "Sectors"}, "unit": {"name": "names", "sector": "sectors"},
        "h_group": {"name": "Name", "sector": "Sector"}, "unclassified": "Unclassified", "lines": "lines",
        "top_g": "Top {n} {unit}", "rest_g": "All other {unit} ({k})",
        "n_group": "Lines are grouped by {what} as the issuer lists it and their weights added ({lines} lines in {groups} groups). ", "what": {"name": "name", "sector": "sector"},
        "n_diffuse": "The fund holds {k} lines and the top {n} are only {x:.1f}% of the listed weights, so single lines say little about concentration; grouping by sector or by name is more informative. ",
        "sub": "{basis} · Holdings as of {as_of}{age} · {issuer}", "age": " ({n} days old)", "sub_unknown": "{basis} · Holdings date not stated · {issuer}",
        "h_rank": "#", "h_name": "Holding", "h_weight": "Weight (%)", "h_cum": "Cumul. (%)", "h_sector": "Sector",
        "top": "Top {n} holdings", "rest": "All other holdings ({k})", "excl": "Not ranked: {kinds}", "kind_short": {"cash": "cash", "treasury": "Treasury bills", "option": "options", "other": "other"},
        "physical": "Shares held", "swap": "Swap exposure", "na": "NA",
        "foot": ("{pre}Source: {src}; as of {as_of}; retrieved {got}. Weights are as reported by the issuer ({basis}). {notes}"
                 "Holdings change daily and can differ from the issuer's website after this date. All corporate names and market data shown above are for "
                 "illustrative purposes only and are not a recommendation, offer to sell, or a solicitation of an offer to buy any security. "
                 "<b>Past performance is no guarantee of future results.</b>"),
        "n_exposure": "Rankings combine each stock with swaps on the same stock, as the issuer's own top-holdings view does; swap weights are as reported and their notional basis is not independently verified. ",
        "n_excluded": "Not ranked: {items}. ", "n_negcash": "Negative cash offsets the swap exposure above. ",
        "n_merged": "Share classes of the same company are added together ({names}). ",
        "n_lines": "Every line is ranked as listed by the issuer; swaps, cash and Treasury bills are not combined or removed. ",
        "n_unmatched": "Swaps without a matching physical position are ranked on their own. ",
        "n_na": "{k} holding(s) have no reported weight and are not ranked. ",
        "n_total": "Listed weights add up to {t:.1f}%. ", "n_issuer_date": "The issuer dates this file {issuer_date} (the next trading day); its weights use the {as_of} closing prices. ", "n_few": "The file lists only {k} holdings that can be ranked. ",
        "kind": {"cash": "cash and money-market funds {w:.{dp}f}%", "treasury": "Treasury bills and notes {w:.{dp}f}%", "option": "options {w:+.{dp}f}%", "other": "other {w:.{dp}f}%"},
        "warn": "Data notes: {w}. ", "lang": "en",
    },
    "zh": {
        "title": "{name} ({sym}) · 前 {n} 大{unit_title}", "title_sym": "{sym} · 前 {n} 大{unit_title}",
        "unit_title": {"holding": "持仓", "name": "名称", "sector": "行业"}, "unit": {"name": "名称", "sector": "行业"},
        "h_group": {"name": "名称", "sector": "行业"}, "unclassified": "未分类", "lines": "行",
        "top_g": "前 {n} 大{unit}合计", "rest_g": "其余{unit}（{k} 项）",
        "n_group": "按发行人列示的{what}把各行归类并相加权重（{lines} 行归为 {groups} 组）。", "what": {"name": "名称", "sector": "行业"},
        "n_diffuse": "该基金共 {k} 行，前 {n} 大合计仅占已列示权重的 {x:.1f}%，单行排名说明不了集中度；按行业或名称归类更有信息量。",
        "sub": "{basis} · 持仓截至 {as_of}{age} · {issuer}", "age": "（距数据获取日 {n} 天）", "sub_unknown": "{basis} · 未注明持仓日期 · {issuer}",
        "h_rank": "#", "h_name": "持仓", "h_weight": "权重 (%)", "h_cum": "累计 (%)", "h_sector": "行业",
        "top": "前 {n} 大合计", "rest": "其余持仓（{k} 项）", "excl": "未参与排名：{kinds}", "kind_short": {"cash": "现金", "treasury": "国债", "option": "期权", "other": "其他"},
        "physical": "持有股份", "swap": "掉期敞口", "na": "NA",
        "foot": ("{pre}资料来源：{src}；持仓截至 {as_of}；数据获取于 {got}。权重以发行人披露为准（{basis}）。{notes}"
                 "持仓每日变化，此日期之后可能与发行人网站不同。以上公司名称及市场数据仅作说明用途，不构成任何证券的推荐、出售要约或购买要约邀请。"
                 "<b>过往业绩不代表未来表现。</b>"),
        "n_exposure": "排名将每只股票与同一股票上的掉期敞口相加，与发行人自己的前十大持仓口径一致；掉期权重按披露原样列示，其名义金额口径未独立核实。",
        "n_excluded": "未参与排名：{items}。", "n_negcash": "负现金用于对冲上述掉期敞口。",
        "n_merged": "同一公司的不同股份类别已合并（{names}）。",
        "n_lines": "按发行人列示的每一行直接排名；掉期、现金和国债未合并或剔除。",
        "n_unmatched": "没有对应现货持仓的掉期单独排名。",
        "n_na": "{k} 项持仓未披露权重，不参与排名。",
        "n_total": "已列示权重合计 {t:.1f}%。", "n_issuer_date": "发行人把此文件标注为 {issuer_date}（下一个交易日），其权重按 {as_of} 的收盘价计算。", "n_few": "文件中可排名的持仓只有 {k} 项。",
        "kind": {"cash": "现金及货币基金 {w:.{dp}f}%", "treasury": "国债及票据 {w:.{dp}f}%", "option": "期权 {w:+.{dp}f}%", "other": "其他 {w:.{dp}f}%"},
        "warn": "数据说明：{w}。", "lang": "zh-Hant",
    },
}
BASIS = {"en": {"% of net assets": "% of net assets", "% of portfolio (economic exposure)": "% of portfolio (economic exposure)"},
         "zh": {"% of net assets": "占净资产比例", "% of portfolio (economic exposure)": "占投资组合比例（经济敞口）"}}
ISSUER_ZH = {"State Street (SPDR)": "道富（SPDR）", "BlackRock iShares": "贝莱德 iShares", "Vanguard": "领航 Vanguard", 
             "NEOS": "NEOS", "Roundhill": "Roundhill", "Tema ETFs": "Tema ETFs", "User-provided file": "用户提供的文件"}


def class_key(name):
    n = re.sub(r"[,.]", "", name.lower())
    n = re.sub(r"\b(class|cl|series)\s+[a-c]\b|\s-\s[a-c]$|\b(ordinary|common)\s+shares?\b", "", n)
    return re.sub(r"\s+", " ", n).strip()


def build_rows(data, mode="exposure", merge_classes=False):
    """Return (ranked rows, excluded totals by kind, notes dict). A row has name, ticker, sector, physical, swap, total."""
    held = data["holdings"]
    notes = {"merged": [], "unmatched": False, "na": 0}
    if mode == "lines":
        rows = [{"name": h["name"], "ticker": h["ticker"], "sector": h["sector"], "physical": h["weight"], "swap": 0.0, "total": h["weight"],
                 "base": h.get("base_name") or h["name"], "count": 1} for h in held]
        ranked = [r for r in rows if r["total"] is not None]
        notes["na"] = len(rows) - len(ranked)
        ranked.sort(key=lambda r: (-r["total"], r["name"]))
        return ranked, {}, notes
    equity_kinds = ("equity",) if any(h["kind"] == "equity" for h in held) else ("bond", "other")
    base = {}
    for h in held:
        if h["kind"] in equity_kinds:
            key = h["id"] or f"{h['ticker']}|{h['name']}"
            base.setdefault(key, []).append(h)
    rows = {}
    for key, hs in base.items():
        top = hs[0]
        rows[key] = {"name": top["name"], "ticker": top["ticker"], "sector": top["sector"], "physical": 0.0, "swap": 0.0, "total": 0.0, "na": False,
                     "base": top.get("base_name") or top["name"], "count": 1}
        for h in hs:
            if h["weight"] is None:
                rows[key]["na"] = True
            else:
                rows[key]["physical"] += h["weight"]
    for h in held:
        if h["kind"] != "swap":
            continue
        key = h.get("underlying_id")
        if key not in rows:
            key = f"swap|{key}|{h['name']}"
            rows.setdefault(key, {"name": h["name"], "ticker": "", "sector": None, "physical": 0.0, "swap": 0.0, "total": 0.0, "na": False,
                                  "base": h["name"], "count": 1})
            notes["unmatched"] = True
        if h["weight"] is None:
            rows[key]["na"] = True
        else:
            rows[key]["swap"] += h["weight"]
    out = list(rows.values())
    for r in out:
        r["total"] = r["physical"] + r["swap"]
    if merge_classes:
        groups = {}
        for r in out:
            groups.setdefault(class_key(r["name"]), []).append(r)
        out = []
        for g in groups.values():
            if len(g) > 1:
                g.sort(key=lambda r: -r["total"])
                merged = dict(g[0], physical=sum(r["physical"] for r in g), swap=sum(r["swap"] for r in g), total=sum(r["total"] for r in g),
                              count=sum(r["count"] for r in g),
                              ticker=" / ".join(r["ticker"] for r in g if r["ticker"]), na=any(r["na"] for r in g))
                notes["merged"].append(g[0]["name"])
                out.append(merged)
            else:
                out.append(g[0])
    ranked = [r for r in out if not r["na"]]
    notes["na"] = len(out) - len(ranked)
    ranked.sort(key=lambda r: (-r["total"], r["name"]))
    excluded = {}
    for h in held:
        if h["kind"] in EXCLUDED_KINDS or (h["kind"] == "other" and "equity" in equity_kinds) or (h["kind"] == "bond" and "equity" in equity_kinds):
            if h["weight"] is not None:
                k = h["kind"] if h["kind"] in EXCLUDED_KINDS else "other"
                excluded[k] = excluded.get(k, 0.0) + h["weight"]
    return ranked, excluded, notes


def age_tag(data, L):
    """' (42 days old)' when the holdings date is well before the retrieval date, so a stale chart says so in its subtitle."""
    try:
        age = (dt.date.fromisoformat(data["retrieved_at"][:10]) - dt.date.fromisoformat(data["as_of"])).days
    except (KeyError, TypeError, ValueError):
        return ""
    return L["age"].format(n=age) if age > STALE_DAYS else ""


def decimals(data):
    """One decimal when every reported weight has at most one (so 14.4 is not shown as 14.40); otherwise two."""
    ws = [h["weight"] for h in data["holdings"] if h["weight"] is not None]
    return 1 if ws and all(abs(w * 10 - round(w * 10)) < 1e-6 for w in ws) else 2


def group_rows(rows, by, L):
    """Add the ranked lines of one issuer name (by='name') or one sector (by='sector') together."""
    if by == "sector" and not any(r["sector"] for r in rows):
        raise ValueError("this file has no sector data; use --by holding or --by name")
    groups = {}
    for r in rows:
        label = r["base"] if by == "name" else (r["sector"] or L["unclassified"])
        g = groups.setdefault(label.lower(), {"name": label, "ticker": "", "sector": None, "physical": 0.0, "swap": 0.0, "total": 0.0, "count": 0, "base": label})
        for k in ("physical", "swap", "total", "count"):
            g[k] += r[k]
    return sorted(groups.values(), key=lambda g: (-g["total"], g["name"]))


def fnum(v, dp=2):
    if v is None:
        return "NA"
    t = format(abs(v), f".{dp}f")
    return f'<span class="sgn">-</span>{t}' if v < 0 else t


def display_name(row, lang, names, lines_label=None):
    local = (names.get(row["ticker"]) or {}).get(lang) if row["ticker"] else None
    label = escape(local or row["name"])
    if lines_label and row["count"] > 1:   # a group: say how many lines were added together
        return label + f' <span class="tk">({row["count"]:,} {lines_label})</span>'
    return label + (f' <span class="tk">({escape(row["ticker"])})</span>' if row["ticker"] else "")


def build_html(data, lang, theme="light", top=13, mode="exposure", merge_classes=False, names=None, by="holding"):
    names = names or {}
    L, T = S[lang], THEMES[theme]
    ranked, excluded, notes = build_rows(data, mode, merge_classes)
    if not ranked:
        raise ValueError("no holdings with a reported weight to rank")
    if by not in GROUPS:
        raise ValueError(f"unknown grouping {by!r}; choose from {', '.join(GROUPS)}")
    n_lines = len(ranked)
    if by != "holding":
        ranked = group_rows(ranked, by, L)
    shown = ranked[:top]
    dp = decimals(data)
    n = len(shown)
    scale = max(r["total"] for r in shown) or 1
    has_sector = by == "holding" and any(r["sector"] for r in shown)
    has_swap = any(r["swap"] for r in shown)
    cum, body = 0.0, []
    for i, r in enumerate(shown, 1):
        cum += r["total"]
        phys = max(r["physical"], 0) / scale * 100
        swap = max(r["swap"], 0) / scale * 100
        bar = (f'<div class="bar"><i class="fp" style="width:{phys:.2f}%"></i><i class="fs" style="width:{swap:.2f}%"></i></div>')
        sector = f'<td class="sec">{escape(r["sector"] or "")}</td>' if has_sector else ""
        body.append(f'<tr><td class="rk">{i}</td><td class="name" title="{escape(r["name"], quote=True)}">{display_name(r, lang, names, L["lines"] if by != "holding" else None)}</td><td class="bars">{bar}</td>'
                    f'<td class="num">{fnum(r["total"], dp)}</td><td class="num cum">{fnum(cum, dp)}</td>{sector}</tr>')
    span = 5 + (1 if has_sector else 0)
    rest = ranked[n:]
    rest_w = sum(r["total"] for r in rest)
    unit = L["unit"].get(by)
    sums = [((L["top"] if by == "holding" else L["top_g"]).format(n=n, unit=unit), cum, None)]
    if rest:
        sums.append(((L["rest"] if by == "holding" else L["rest_g"]).format(k=f"{len(rest):,}", unit=unit), rest_w, None))
    excl_total = sum(excluded.values())
    if excluded:
        sums.append((L["excl"].format(kinds=("、" if lang == "zh" else ", ").join(L["kind_short"][k] for k in excluded)), excl_total, None))
    for j, (label, w, cumulative) in enumerate(sums):
        sec = '<td></td>' if has_sector else ""
        body.append(f'<tr class="sum{" first" if j == 0 else ""}"><td></td><td class="name">{label}</td><td></td><td class="num">{fnum(w, dp)}</td><td class="num cum">'
                    f'{"" if cumulative is None else fnum(cumulative, dp)}</td>{sec}</tr>')
    basis = BASIS[lang].get(data["weight_basis"], data["weight_basis"])
    issuer = ISSUER_ZH.get(data["issuer"], data["issuer"]) if lang == "zh" else data["issuer"]
    as_of = data.get("as_of")
    sub = (L["sub"] if as_of else L["sub_unknown"]).format(basis=basis, as_of=as_of, issuer=issuer, age=age_tag(data, L))
    name = data.get("name")
    ut = L["unit_title"][by]
    title = (L["title"].format(name=escape(name), sym=escape(data["symbol"]), n=n, unit_title=ut) if name
             else L["title_sym"].format(sym=escape(data["symbol"]), n=n, unit_title=ut))
    sep = "、" if lang == "zh" else ", "
    note = ""
    if mode == "lines":
        note += L["n_lines"]
    elif has_swap or any(h["kind"] == "swap" for h in data["holdings"]):
        note += L["n_exposure"] + (L["n_unmatched"] if notes["unmatched"] else "")
    if excluded and mode != "lines":
        items = sep.join(L["kind"][k].format(w=w, dp=dp) for k, w in excluded.items())
        note += L["n_excluded"].format(items=items) + (L["n_negcash"] if excluded.get("cash", 0) < 0 else "")
    if notes["merged"]:
        note += L["n_merged"].format(names=sep.join(escape(m) for m in notes["merged"][:4]) + ("…" if len(notes["merged"]) > 4 else ""))
    if notes["na"]:
        note += L["n_na"].format(k=notes["na"])
    total = sum(h["weight"] for h in data["holdings"] if h["weight"] is not None)
    note += L["n_total"].format(t=total)
    if data.get("issuer_date") and data.get("as_of") and data["issuer_date"] != data["as_of"]:
        note += L["n_issuer_date"].format(issuer_date=data["issuer_date"], as_of=data["as_of"])
    if by != "holding":
        note += L["n_group"].format(what=L["what"][by], lines=f"{n_lines:,}", groups=f"{len(ranked):,}")
    elif n_lines >= DIFFUSE_LINES:
        pool = sum(r["total"] for r in ranked)
        share = cum / pool * 100 if pool > 0 else 100.0
        if share < DIFFUSE_SHARE:
            note += L["n_diffuse"].format(k=f"{n_lines:,}", n=n, x=share)
    if by == "holding" and len(ranked) < top:
        note += L["n_few"].format(k=len(ranked))
    warnings = [w for w in data.get("warnings", []) if "no reported weight" not in w and "add up to" not in w]
    if warnings:
        note += L["warn"].format(w=escape("; ".join(w.rstrip(".") for w in warnings)))
    got = (data.get("retrieved_at") or "")[:10] or "NA"
    src = escape(data["source"])
    pre = escape((data.get("note") or {}).get(lang, ""))
    pre = pre + " " if pre else ""
    foot = L["foot"].format(pre=pre, src=src, as_of=as_of or "NA", got=got, basis=basis, notes=note)
    legend = ""
    if has_swap:
        legend = (f'<div class="legend"><span class="lg"><i class="sw fp"></i>{L["physical"]}</span>'
                  f'<span class="lg"><i class="sw fs"></i>{L["swap"]}</span></div>')
    head_sector = f'<th class="l">{L["h_sector"]}</th>' if has_sector else ""
    cols = ('<col style="width:30px"><col style="width:auto"><col style="width:110px"><col style="width:66px"><col style="width:66px">'
            + ('<col style="width:150px">' if has_sector else ""))
    css = font_face_css() + f"""
body{{margin:0;background:{T['bg']};font-family:{FONT};-webkit-font-smoothing:antialiased}}
@page{{margin:0}}
#wrap{{width:736px;padding:12px;background:{T['bg']}}}
.box{{border:1px solid {T['border']}}}
.band{{background:{T['band']};color:{T['band_text']};text-align:center;padding:9px 10px 8px}}
.band .t{{font-size:15px;font-weight:700}} .band .s{{font-size:12.5px;font-weight:500;margin-top:2px}}
.legend{{padding:8px 12px 0;font-size:12.5px;color:{T['ink']};display:flex;gap:16px}}
.lg{{display:inline-flex;align-items:center;gap:6px}}
.sw{{display:inline-block;width:22px;height:9px}}
.fp{{background:{T['ser'][0]}}} .fs{{background:repeating-linear-gradient(135deg,{T['ser'][0]} 0 2px,{T['bg']} 2px 4px);outline:1px solid {T['ser'][0]};outline-offset:-1px}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;font-size:13px;color:{T['tbl']}}}
th{{background:{T['band']};color:{T['band_text']};font-weight:600;text-align:right;padding:5px 12px 5px 8px;font-size:12.5px;line-height:1.25;vertical-align:bottom}}
th.l{{text-align:left}}
td{{text-align:right;padding:0 12px 0 8px;height:26px;border-top:1px solid {T['rule']};font-feature-settings:"tnum" 1;white-space:nowrap}}
td.rk{{text-align:center;padding:0;color:{T['muted']}}}
td.name{{text-align:left;overflow:hidden;text-overflow:ellipsis;padding-left:8px}}
td.sec{{text-align:left;overflow:hidden;text-overflow:ellipsis;color:{T['muted']};font-size:11.5px;padding-right:6px}}
td.bars{{padding:0 8px 0 4px}}
.tk{{color:{T['muted']};font-size:12px}}
.bar{{display:flex;height:11px;background:transparent}}
.bar i{{display:block;height:100%}}
tr.sum td{{color:{T['ink']};font-weight:600;background:{T['bg']}}}
tr.first td{{border-top:1px solid {T['border']}}}
.sgn{{font-feature-settings:"tnum" 0}}
.foot{{margin-top:7px;font-size:10px;color:{T['foot']};line-height:1.4}} .foot b{{font-weight:600;color:{T['foot_b']}}}
"""
    html = (f'<!doctype html><html lang="{L["lang"]}"><head><meta charset="utf-8"><title>{escape(data["symbol"])} top holdings</title><style>{css}</style></head>'
            f'<body><div id="wrap"><div class="box"><div class="band"><div class="t">{title}</div><div class="s">{escape(sub)}</div></div>{legend}'
            f'<table><colgroup>{cols}</colgroup><thead><tr><th>{L["h_rank"]}</th><th class="l">{L["h_name"] if by == "holding" else L["h_group"][by]}</th><th></th>'
            f'<th>{L["h_weight"]}</th><th>{L["h_cum"]}</th>{head_sector}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'
            f'<div class="foot">{foot}</div></div></body></html>')
    return traditional_html(html) if lang == "zh" else html


def main():
    ap = argparse.ArgumentParser(description="Render an ETF top-N holdings chart from fetch_holdings.py output.")
    ap.add_argument("data", help="holdings JSON from fetch_holdings.py")
    ap.add_argument("prefix", help="output prefix, e.g. out/qqq -> out/qqq_en.html / .png")
    ap.add_argument("--top", type=int, default=13, help="how many holdings to show (default 13)")
    ap.add_argument("--mode", choices=("exposure", "lines"), default="exposure", help="see the module docstring")
    ap.add_argument("--by", choices=GROUPS, default="holding", help="rank single lines (default), or add lines together by issuer name or by sector")
    ap.add_argument("--merge-classes", action="store_true", help="add share classes of one company together")
    ap.add_argument("--names", help='JSON {"NVDA": {"zh": "英伟达"}} for local-language names')
    ap.add_argument("--langs", default="en,zh")
    ap.add_argument("--no-png", action="store_true", help="write HTML only (no Playwright needed)")
    ap.add_argument("--pdf", action="store_true", help="also write a vector PDF")
    ap.add_argument("--scale", type=float, default=2, help="PNG pixel density (default 2; use 3 for print)")
    ap.add_argument("--theme", choices=sorted(THEMES), default="light", help="light (default) or dark")
    a = ap.parse_args()
    if not 1 <= a.top <= MAX_TOP:
        sys.exit(f"error: --top must be between 1 and {MAX_TOP}")
    try:
        data = json.loads(Path(a.data).read_text(encoding="utf-8"))
        names = json.loads(Path(a.names).read_text(encoding="utf-8")) if a.names else {}
    except (OSError, ValueError) as e:
        sys.exit(f"error: cannot read input: {e}")
    if not isinstance(data, dict) or not data.get("holdings"):
        sys.exit(f"error: {a.data} is not output of fetch_holdings.py (no holdings list)")
    langs = [x.strip() for x in a.langs.split(",")]
    bad = [l for l in langs if l not in S]
    if bad:
        sys.exit(f"error: unsupported language(s): {', '.join(bad)} (available: {', '.join(S)})")
    try:
        htmls = {l: build_html(data, l, a.theme, a.top, a.mode, a.merge_classes, names, a.by) for l in langs}
    except (ValueError, KeyError) as e:
        sys.exit(f"error: {e}")
    Path(a.prefix).parent.mkdir(parents=True, exist_ok=True)
    for l, h in htmls.items():
        Path(f"{a.prefix}_{l}.html").write_text(h, encoding="utf-8")
        print(f"wrote {a.prefix}_{l}.html")
    if not a.no_png or a.pdf:
        render_files(htmls, a.prefix, a.scale, png=not a.no_png, pdf=a.pdf)
    ranked, _, _ = build_rows(data, a.mode, a.merge_classes)
    print(f"{data['symbol']}: top {min(a.top, len(ranked))} = {sum(r['total'] for r in ranked[:a.top]):.2f}% | as of {data.get('as_of') or 'NA'}")


if __name__ == "__main__":
    main()
