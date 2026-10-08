"""Render a Schwab-style performance table (EN + ZH) from a JSON spec.

Usage: python3 render_table.py spec.json OUT_PREFIX [--langs en,zh] [--no-png] [--pdf] [--scale 2] [--theme light|dark]
Writes OUT_PREFIX_en.html/.png and OUT_PREFIX_zh.html/.png (2x).
Missing output directories are created. --langs limits the languages rendered,
--no-png writes HTML only (no Playwright needed). --scale sets PNG pixel density (default 2).

Spec:
{
  "langs": {
    "en": {"title": "...", "h1": [5 strings], "h2": [5 strings], "foot": "html", "foot_size": "10px"},
    "zh": {...}
  },
  "formats": ["pct", "pct", "money", "raw"],        # one per numeric column (cols 2-5)
  "rows": [
    {"ticker": "NVDA", "name": {"en": "NVIDIA Corp", "zh": "英伟达"}, "cells": [25.7, 4.4, 24.2, 233.95]},
    {"name": {"en": "S&P 500", "zh": "标普 500"}, "cells": [12.8, null, null, null], "bench": true}
  ]
}
Rows are sorted by cells[0] descending; bench rows are bold, have no ticker, and null renders as NA.
Formats: pct = 1 decimal, money = 2 decimals with thousands separator, raw = string as given.
"""
import argparse
import json
import sys
from pathlib import Path

from fonts import font_face_css
from render_common import THEMES, render_files
from institutional_tables import STYLES, build_html as institutional_html
from localization import traditional_html

FONT_STACK = ('"Inter", "Helvetica Neue", Helvetica, Arial, '
              '"Noto Sans CJK TC", "Source Han Sans TC", "PingFang TC", "Microsoft JhengHei", sans-serif')


def fmt(v, kind):
    if v is None:
        return "NA"
    if kind == "raw":
        return str(v)
    t = format(abs(v), ".1f" if kind == "pct" else ",.2f")
    return f'<span class="sgn">-</span>{t}' if v < 0 else t


def build_html(spec, lang, theme="light", style=None):
    style = style or spec.get("style", "schwab")
    if style not in STYLES:
        raise ValueError(f"unknown table style: {style}")
    if style != "schwab":
        return institutional_html(spec, lang, style, theme)
    L = spec["langs"][lang]
    T = THEMES[theme]
    rows = sorted(spec["rows"], key=lambda r: r["cells"][0], reverse=True)
    body = []
    for r in rows:
        name = r["name"][lang]
        if r.get("ticker") and not r.get("bench"):
            name += f' <span class="tk">({r["ticker"]})</span>'
        cells = "".join(f"<td>{fmt(v, k)}</td>" for v, k in zip(r["cells"], spec["formats"]))
        body.append(f'<tr class="{"bench" if r.get("bench") else ""}"><td class="name">{name}</td>{cells}</tr>')
    h1 = "".join(f"<th>{t}</th>" for t in L["h1"])
    h2 = "".join(f"<th>{t}</th>" for t in L["h2"])
    html = f"""<!doctype html><html lang="{'zh-Hant' if lang == 'zh' else 'en'}"><head><meta charset="utf-8">
<title>{L['title']}</title><style>
{font_face_css()}
body {{ margin:0; background:{T['bg']}; font-family:{FONT_STACK}; -webkit-font-smoothing:antialiased; }}
tbody td:not(.name) {{ font-feature-settings:"tnum" 1, "lnum" 1; }}
.sgn {{ font-feature-settings:"tnum" 0; }}
.tk {{ font-family:"Inter", "Helvetica Neue", Helvetica, Arial, sans-serif; letter-spacing:0.2px; }}
#wrap {{ width:760px; padding:12px; background:{T['bg']}; }}
table {{ width:100%; border-collapse:collapse; border:1px solid {T['border']}; table-layout:fixed; }}
col.c1 {{ width:30%; }} col.c2 {{ width:13%; }} col.cx {{ width:19%; }}
thead th {{ background:{T['band']}; color:{T['band_text']}; font-weight:600; font-size:13.5px; line-height:1.25;
           text-align:right; padding:2px 12px 2px 10px; vertical-align:bottom; white-space:nowrap; }}
thead tr.title th {{ text-align:center; font-size:15px; font-weight:700; padding:9px 10px 5px; letter-spacing:0.1px; }}
thead tr.h2 th {{ padding-bottom:7px; }}
tbody td {{ font-size:13.5px; color:{T['tbl']}; height:26px; padding:0 12px 0 10px; text-align:right;
           border-top:1px solid {T['rule']}; white-space:nowrap; line-height:26px; vertical-align:middle; }}
tbody td.name {{ text-align:left; padding-left:10px; }}
tbody tr.bench td {{ color:{T['ink']}; font-weight:600; }}
.foot {{ margin-top:7px; font-size:{L.get('foot_size', '10px')}; color:{T['foot']}; line-height:1.4; }}
.foot b {{ font-weight:600; color:{T['foot_b']}; }}
</style></head><body><div id="wrap">
<table>
<colgroup><col class="c1"><col class="c2"><col class="cx"><col class="cx"><col class="cx"></colgroup>
<thead>
<tr class="title"><th colspan="5">{L['title']}</th></tr>
<tr class="h1">{h1}</tr>
<tr class="h2">{h2}</tr>
</thead>
<tbody>
{chr(10).join(body)}
</tbody></table>
<div class="foot">{L['foot']}</div>
</div></body></html>"""
    return traditional_html(html) if lang == "zh" else html


def load_spec(spec_path):
    try:
        with open(spec_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit(f"error: spec file not found: {spec_path}")
    except json.JSONDecodeError as e:
        sys.exit(f"error: {spec_path} is not valid JSON: {e}")


def pick_langs(spec, wanted):
    available = list(spec["langs"])
    if not wanted:
        return available
    missing = [l for l in wanted if l not in available]
    if missing:
        sys.exit(f"error: language(s) {', '.join(missing)} not in spec (available: {', '.join(available)})")
    return wanted


def main():
    ap = argparse.ArgumentParser(description="Render a Schwab-style performance table from a JSON spec.")
    ap.add_argument("spec", help="path to the spec JSON")
    ap.add_argument("prefix", help="output prefix, e.g. out/neural9 -> out/neural9_en.html / .png")
    ap.add_argument("--langs", help="comma-separated languages to render (default: all in the spec)")
    ap.add_argument("--no-png", action="store_true", help="write HTML only")
    ap.add_argument("--pdf", action="store_true", help="also write a vector PDF")
    ap.add_argument("--theme", choices=sorted(THEMES), default="light", help="light (default) or dark")
    ap.add_argument("--style", choices=STYLES, help="report template (default: spec.style, or schwab)")
    ap.add_argument("--scale", type=float, default=2, help="PNG pixel density (default 2; use 3 for print)")
    args = ap.parse_args()

    spec = load_spec(args.spec)
    langs = pick_langs(spec, [l.strip() for l in args.langs.split(",")] if args.langs else None)
    Path(args.prefix).parent.mkdir(parents=True, exist_ok=True)

    try:
        htmls = {lang: build_html(spec, lang, args.theme, args.style) for lang in langs}
    except (ValueError, RuntimeError) as exc:
        sys.exit(f"error: {exc}")
    for lang, html in htmls.items():
        Path(f"{args.prefix}_{lang}.html").write_text(html, encoding="utf-8")
        print(f"wrote {args.prefix}_{lang}.html")
    if not args.no_png or args.pdf:
        render_files(htmls, args.prefix, args.scale, png=not args.no_png, pdf=args.pdf)


if __name__ == "__main__":
    main()
