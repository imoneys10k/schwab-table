"""Render a Schwab-style price-performance chart (EN + ZH) from fetch_prices.py / csv_to_prices.py output.

Usage: python3 render_chart.py spec.json OUT_PREFIX [--langs en,zh] [--no-png] [--pdf] [--scale 2] [--theme light|dark]

Spec:
{
  "data": "data/neural9.json",                 # output of fetch_prices.py or csv_to_prices.py
  "symbols": ["MU", "NVDA"],                    # optional subset / order (default: all non-benchmark series)
  "names": {"MU": {"en": "Micron Technology Inc", "zh": "美光科技"}},
  "benchmarks": ["SPY"],                        # optional subset / order of the benchmarks in the data file (default: all of them)
  "benchmark_name": {"en": "S&P 500 (SPY)", "zh": "标普 500 (SPY)"},   # first benchmark; or {"SPY": {"en": ..., "zh": ...}, "COMP": {...}} per symbol
  "colors": {"MU": "#2a78d6"},                  # optional per-symbol line colours (lines layout)
  "layout": "auto",                             # auto | lines | multiples   (auto: <=5 symbols lines, else multiples)
  "y_scale": "auto",                            # auto (log when the range is wide) | linear | log
  "drawdown": true,                             # add a drawdown-from-peak panel
  "table": true,                                # lines layout: summary table under the chart
  "start": "2026-01-01", "end": "2026-10-02",   # optional; default = the data file's range. start = base date: indexed to 100 at the last close on or before it
  "title": {"en": "...", "zh": "..."},          # optional
  "note": {"en": "...", "zh": "..."}            # optional text put at the start of the footnote (e.g. "Hypothetical example")
}
"""
import argparse
import bisect
import datetime as dt
import json
import math
import re
import sys
from pathlib import Path

from fonts import font_face_css
from render_common import THEMES, render_files

FONT = ('"Inter","Helvetica Neue",Helvetica,Arial,"Noto Sans CJK SC","Source Han Sans SC","PingFang SC","Microsoft YaHei",sans-serif')
MAX_SYMBOLS = 9
MAX_LINES = 5

DASHES = ["5 4", "2 3"]

S = {
    "en": {
        "ytd_title": "{y} YTD Price Performance", "range_title": "Price Performance, {a} – {b}",
        "sub": "Indexed to 100 at {base} close · Daily close", "sub_total": "Indexed to 100 at {base} close · Daily adjusted close · Total return", "log": " · Log scale",
        "ret_ytd": ("YTD", "return (%)"), "ret": ("Period", "return (%)"), "vol": ("Ann.", "volatility (%)"),
        "mdd": ("Max", "drawdown (%)"), "last": ("Last", "price ($)"), "bench": "Benchmark",
        "dd_title": "Drawdown from peak (%)", "same": "Same scale in every panel", "stock": "Stock",
        "foot": ("Source: {src}, as of {end}; retrieved {got}. Indexed to 100 at the {base} close. {basis}Annualized volatility is the standard deviation of daily "
                 "returns × √252; maximum drawdown is the largest peak-to-trough decline over the period. {bench}All corporate names and market data shown above "
                 "are for illustrative purposes only and are not a recommendation, offer to sell, or a solicitation of an offer to buy any security. "
                 "<b>Past performance is no guarantee of future results.</b>"),
        "basis_price": "Returns are price returns (excluding dividends) computed from official closing prices. ",
        "basis_total": "Returns are total returns (dividends reinvested) computed from adjusted closing prices supplied by the user. ",
        "bench_etf": "{b}: exchange-traded fund(s) used here as proxies for their indexes; not the indexes themselves and cannot replicate them exactly. ",
        "bench_idx": "Indexes are unmanaged, do not incur management fees, costs and expenses and cannot be invested in directly. ",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], "lang": "en",
        "tip_d": "{m}/{d}/{y}",
    },
    "zh": {
        "ytd_title": "{y} 年股价表现（年初至今）", "range_title": "股价表现，{a} – {b}",
        "sub": "以 {base} 收盘价为 100 · 日收盘价", "sub_total": "以 {base} 收盘价为 100 · 日复权收盘价 · 总回报", "log": " · 对数刻度",
        "ret_ytd": ("年初", "至今 (%)"), "ret": ("区间", "涨跌幅 (%)"), "vol": ("年化", "波动率 (%)"),
        "mdd": ("最大", "回撤 (%)"), "last": ("最新", "收盘价 ($)"), "bench": "基准",
        "dd_title": "距前高回撤 (%)", "same": "各图纵轴一致", "stock": "个股",
        "foot": ("资料来源：{src}，截至 {end}，数据获取于 {got}。以 {base} 收盘价为 100。{basis}"
                 "年化波动率为日回报标准差 × √252；最大回撤为区间内自前高的最大跌幅。{bench}"
                 "以上公司名称及市场数据仅作说明用途，不构成任何证券的推荐、出售要约或购买要约邀请。<b>过往业绩不代表未来表现。</b>"),
        "basis_price": "回报为由官方收盘价计算的价格回报（不含股息）。",
        "basis_total": "回报为由用户提供的复权收盘价计算的总回报（股息再投资）。",
        "bench_etf": "{b}：交易所交易基金，此处仅用作其对应指数的替代，并非指数本身，也无法完全复制指数。",
        "bench_idx": "指数不受管理，不产生管理费及其他费用，且不可直接投资。",
        "months": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"], "lang": "zh-CN",
        "tip_d": "{y}/{m}/{d}",
    },
}
ZH_SRC = {"Nasdaq (official closing prices, split-adjusted)": "纳斯达克（官方收盘价，已按拆股调整）",
          "S&P 500 (S&P Dow Jones Indices, via FRED)": "标普 500（标普道琼斯指数公司，经 FRED 转载）",
          "Nasdaq Composite (Nasdaq Global Indexes, via FRED)": "纳斯达克综合指数（Nasdaq Global Indexes，经 FRED 转载）",
          "Synthetic sample data (not real market data)": "虚构示例数据（非真实行情）"}


def fdate(d):
    return f"{d.month}/{d.day}/{d.year}"


def f1(v, sign=False):
    t = f"{abs(v):.1f}"
    return ("-" if v < 0 else ("+" if sign else "")) + t


# ---- data ---------------------------------------------------------------------
class Series:
    """One symbol indexed to 100 at the last close on or before `base`, trimmed to `end`."""

    def __init__(self, sym, raw_pts, base, end, is_bench=False, basis="price", source=""):
        self.sym, self.is_bench, self.basis, self.source = sym, is_bench, basis, source
        pts = sorted((dt.date.fromisoformat(d), c) for d, c in raw_pts)
        i = bisect.bisect_right([d for d, _ in pts], base) - 1
        if i < 0 or (base - pts[i][0]).days > 7:
            raise ValueError(f"{sym}: no close on or within 7 days before the base date {base}")
        self.base_date, base_close = pts[i]
        pts = [(d, c) for d, c in pts[i:] if d <= end]
        if len(pts) < 2:
            raise ValueError(f"{sym}: fewer than two closes between {self.base_date} and {end}")
        self.dates = [d for d, _ in pts]
        self.close = [c for _, c in pts]
        self.idx = [c / base_close * 100 for c in self.close]
        peak, dd = self.idx[0], []
        for v in self.idx:
            peak = max(peak, v)
            dd.append((v / peak - 1) * 100)
        self.dd = dd
        rets = [self.idx[k + 1] / self.idx[k] - 1 for k in range(len(self.idx) - 1)]
        m = sum(rets) / len(rets)
        self.vol = math.sqrt(sum((r - m) ** 2 for r in rets) / max(len(rets) - 1, 1)) * math.sqrt(252) * 100
        self.ret = self.idx[-1] - 100
        self.mdd = min(dd)


def load(spec, base_dir):
    d = json.loads((base_dir / spec["data"]).read_text(encoding="utf-8"))
    allpts = d["series"]
    end = dt.date.fromisoformat(spec["end"]) if spec.get("end") else dt.date.fromisoformat(d["end"])
    start = dt.date.fromisoformat(spec["start"]) if spec.get("start") else dt.date.fromisoformat(d["start"])
    end = min(end, max(dt.date.fromisoformat(v["points"][-1][0]) for v in allpts.values()))
    syms = spec.get("symbols") or [k for k, v in allpts.items() if not v["benchmark"]]
    bench_syms = spec.get("benchmarks") or d.get("benchmarks") or ([d["benchmark"]] if d.get("benchmark") else [])
    warnings, series, benches = [], [], []

    def make(sym, is_bench):
        v = allpts[sym]
        return Series(sym, v["points"], start, end, is_bench, v.get("basis", "price"), v.get("source", ""))

    for s in syms:
        if s not in allpts:
            warnings.append(f"{s}: not in data file, left out")
            continue
        try:
            series.append(make(s, False))
        except ValueError as e:
            warnings.append(f"{e}; left out")
    if not series:
        sys.exit("error: no usable series")
    if len(series) > MAX_SYMBOLS:
        warnings.append(f"{len(series)} symbols given, keeping the first {MAX_SYMBOLS}")
        series = series[:MAX_SYMBOLS]
    for b in bench_syms:
        if b not in allpts:
            warnings.append(f"benchmark {b}: not in data file, left out")
            continue
        try:
            benches.append(make(b, True))
        except ValueError as e:
            warnings.append(f"benchmark {e}; left out")
    base = series[0].base_date
    used = series + benches
    if any(x.base_date != base for x in used):
        warnings.append("base dates differ between series (a holiday gap?): " + ", ".join(f"{x.sym}={x.base_date}" for x in used))
    bases = {x.basis for x in used}
    if len(bases) > 1:
        sys.exit("error: price-return and total-return series cannot be mixed in one chart: " + ", ".join(f"{x.sym}={x.basis}" for x in used))
    for k, c in (spec.get("colors") or {}).items():
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", str(c)):
            sys.exit(f"error: colors[{k}] must be a #rrggbb hex value, got {c!r}")
    return d, series, benches, base, end, start, warnings


# ---- scales -------------------------------------------------------------------
def nice_ticks(lo, hi, n=6):
    span = hi - lo
    step = 10 ** math.floor(math.log10(span / n))
    for m in (1, 2, 2.5, 5, 10):
        if span / (step * m) <= n:
            step *= m
            break
    a = math.floor(lo / step + 1e-9) * step
    out = []
    while a <= hi + 1e-9:
        if a >= lo - 1e-9:
            out.append(round(a, 6))
        a += step
    return out


def log_ticks(lo, hi, maxn=8):
    t = []
    for mults in ([1, 2, 5], [1, 1.5, 2, 3, 5, 7], [1, 1.25, 1.5, 2, 2.5, 3, 4, 5, 6, 7, 8, 9]):
        t = []
        k = math.floor(math.log10(lo)) - 1
        while 10 ** k <= hi * 10:
            for m in mults:
                v = m * 10 ** k
                if lo * 0.999 <= v <= hi * 1.001:
                    t.append(v)
            k += 1
        if 4 <= len(t) <= maxn:
            return t
        if len(t) > maxn and mults[-1] == 9:
            return t[:: math.ceil(len(t) / maxn)]
    return t


class Plot:
    def __init__(self, x, y, w, h, lo, hi, d0, d1, log=False):
        self.x, self.y, self.w, self.h, self.lo, self.hi, self.d0, self.d1, self.log = x, y, w, h, lo, hi, d0, d1, log
        self.span = max((d1 - d0).days, 1)

    def px(self, d):
        return self.x + self.w * (d - self.d0).days / self.span

    def py(self, v):
        if self.log:
            f = (math.log(v) - math.log(self.lo)) / (math.log(self.hi) - math.log(self.lo))
        else:
            f = (v - self.lo) / (self.hi - self.lo)
        return self.y + self.h * (1 - f)

    def path(self, dates, vals):
        return "M" + " L".join(f"{self.px(d):.1f},{self.py(v):.1f}" for d, v in zip(dates, vals))


def y_range(series, log):
    lo = min(min(s.idx) for s in series)
    hi = max(max(s.idx) for s in series)
    lo, hi = min(lo, 100), max(hi, 100)
    if log:
        lo, hi = lo * 0.94, hi * 1.06
        t = log_ticks(lo, hi)
        return min(lo, t[0]), max(hi, t[-1]), t
    pad = (hi - lo) * 0.04
    t = nice_ticks(lo - pad, hi + pad)
    return min(lo - pad, t[0]), max(hi + pad, t[-1]), t


def x_ticks(d0, d1, L):
    span = (d1 - d0).days
    m = L["months"]
    out = []
    if span <= 45:  # weekly (Mondays)
        d = d0 + dt.timedelta(days=(7 - d0.weekday()) % 7)
        while d <= d1:
            out.append((d, f"{d.month}/{d.day}"))
            d += dt.timedelta(days=7)
    else:
        step = 1 if span <= 400 else (3 if span <= 1100 else 12)
        y, mo = d0.year, d0.month
        while True:
            d = dt.date(y, mo, 1)
            if d > d1:
                break
            if d >= d0 - dt.timedelta(days=3) and ((mo - 1) % step == 0):
                lab = m[mo - 1] if (step == 1 and span <= 400 and mo != 1) else (f"{m[mo - 1]} {y}" if L["lang"] == "en" else f"{y}年{mo}月")
                if step == 12:
                    lab = str(y)
                out.append((max(d, d0), lab))
            mo += 1
            if mo > 12:
                y, mo = y + 1, 1
    return out


def spread(items, gap, hi):
    """Push labels apart so neighbours are at least `gap` px away; items = [(key, y)] -> {key: y}."""
    items = sorted(items, key=lambda kv: kv[1])
    ys = [y for _, y in items]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    over = ys[-1] - hi
    if over > 0:
        ys = [y - over for y in ys]
    return {k: y for (k, _), y in zip(items, ys)}


def use_log(spec, allk):
    mode = spec.get("y_scale", "auto")
    if mode != "auto":
        return mode == "log"
    return max(max(s.idx) for s in allk) / min(min(s.idx) for s in allk) > 3  # a >3x spread flattens everything else on a linear axis


def is_ytd(start, end):
    return start == dt.date(end.year, 1, 1)


# ---- rendering context ---------------------------------------------------------------
W = 734  # inner width of the box


class Ctx:
    def __init__(self, spec, d, series, benches, base, end, start, lang, theme):
        self.spec, self.d, self.series, self.benches = spec, d, series, benches
        self.base, self.end, self.start, self.lang = base, end, start, lang
        self.L, self.T = S[lang], THEMES[theme]
        self.allk = series + benches
        self.log = use_log(spec, self.allk)
        self.dd_on = bool(spec.get("drawdown", True))
        self.total = series[0].basis == "total"
        self.hov = []
        user = spec.get("colors") or {}
        self.col = {s.sym: user.get(s.sym, self.T["ser"][i % len(self.T["ser"])]) for i, s in enumerate(series)}
        for i, b in enumerate(benches):
            self.col[b.sym] = self.T["bench"][min(i, len(self.T["bench"]) - 1)]

    def dash(self, s):
        return DASHES[min(self.benches.index(s), len(DASHES) - 1)] if s.is_bench else ""

    def name_of(self, sym):
        n = self.spec.get("names", {}).get(sym, {}).get(self.lang)
        return f"{n} ({sym})" if n else sym

    def bench_label(self, b):
        bn = self.spec.get("benchmark_name") or {}
        if self.lang in bn and self.benches and b is self.benches[0]:
            return bn[self.lang]
        n = (bn.get(b.sym) or {}).get(self.lang)
        return n or b.sym

    def bench_short(self, b):
        n = self.bench_label(b).split(" (")[0]
        return n if len(n) <= 10 else (b.sym if len(self.benches) > 1 else self.L["bench"])

    def add_hover(self, p, rows, svg_id):
        """Register a hover panel: rows = [(label, colour, Series)] drawn in plot `p`."""
        xs = sorted({d for _, _, s in rows for d in s.dates})
        self.hov.append({
            "svg": svg_id, "x0": round(p.x, 1), "x1": round(p.x + p.w, 1), "y0": round(p.y, 1), "y1": round(p.y + p.h, 1),
            "dates": [d.isoformat() for d in xs], "xs": [round(p.px(d), 1) for d in xs],
            "rows": [{"n": n, "c": c, "m": {s.dates[i].isoformat(): round(s.idx[i], 2) for i in range(len(s.dates))}} for n, c, s in rows],
        })

    def css(self):
        T = self.T
        return font_face_css() + f"""
body{{margin:0;background:{T['bg']};font-family:{FONT};-webkit-font-smoothing:antialiased}}
@page{{margin:0}}
#wrap{{width:736px;padding:12px;background:{T['bg']};position:relative}}
.box{{border:1px solid {T['border']}}}
.band{{background:{T['band']};color:{T['band_text']};text-align:center;padding:9px 10px 8px}}
.band .t{{font-size:15px;font-weight:700}} .band .s{{font-size:12.5px;font-weight:500;margin-top:2px}}
.legend{{padding:8px 12px 0;font-size:12.5px;color:{T['ink']};display:flex;gap:16px;flex-wrap:wrap;align-items:center}}
.lg{{display:inline-flex;align-items:center;gap:6px}}
.ptitle{{padding:6px 12px 0;font-size:12px;font-weight:700;color:{T['band_text'] if self.T is THEMES['light'] else T['ink']}}}
.foot{{margin-top:7px;font-size:10px;color:{T['foot']};line-height:1.4}} .foot b{{font-weight:600;color:{T['foot_b']}}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;font-size:13px;color:{T['tbl']}}}
th{{background:{T['band']};color:{T['band_text']};font-weight:600;text-align:right;padding:5px 12px 5px 8px;font-size:12.5px;line-height:1.25;vertical-align:bottom}}
td{{text-align:right;padding:0 12px 0 8px;height:25px;border-top:1px solid {T['rule']};font-feature-settings:"tnum" 1;white-space:nowrap}}
th:first-child,td:first-child{{text-align:left;padding-left:12px}}
td svg{{vertical-align:middle;margin-right:7px}}
tr.bench td{{color:{T['ink']};font-weight:600}}
.sgn{{font-feature-settings:"tnum" 0}}
#tip{{position:absolute;display:none;pointer-events:none;z-index:9;background:{T['bg']};color:{T['ink']};border:1px solid {T['axis']};border-radius:6px;padding:7px 9px;font-size:12px;line-height:1.5;box-shadow:0 4px 14px rgba(0,0,0,.25);white-space:nowrap}}
#tip i{{display:inline-block;width:14px;height:3px;margin-right:6px;vertical-align:middle}}
.hov{{fill:transparent;cursor:crosshair}}
"""


# ---- svg building blocks ---------------------------------------------------------
def axes(c, p, ticks, xlabels=True, fs=11, base=100):
    T, g = c.T, []
    for t in ticks:
        y = p.py(t) if t > 0 or not p.log else p.py(p.lo)
        g.append(f'<line x1="{p.x}" x2="{p.x + p.w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{T["axis"] if t == base else T["grid"]}"/>')
        g.append(f'<text x="{p.x - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="{fs}" fill="{T["muted"]}">{t:g}</text>')
    if xlabels:
        for d, lab in x_ticks(p.d0, p.d1, c.L):
            x = p.px(d)
            g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{p.y + p.h}" y2="{p.y + p.h + 4}" stroke="{T["axis"]}"/>')
            g.append(f'<text x="{x:.1f}" y="{p.y + p.h + 17}" text-anchor="middle" font-size="{fs}" fill="{T["muted"]}">{lab}</text>')
    g.append(f'<line x1="{p.x}" x2="{p.x + p.w}" y1="{p.y + p.h}" y2="{p.y + p.h}" stroke="{T["axis"]}"/>')
    return "".join(g)


def line(p, s, col, w=2, dash=""):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{p.path(s.dates, s.idx)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"{da}/>'


def swatch(col, dash="", w=22):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<svg width="{w}" height="8"><line x1="0" x2="{w}" y1="4" y2="4" stroke="{col}" stroke-width="2.5"{d}/></svg>'


def sg(v):
    t = f"{abs(v):.1f}"
    return f'<span class="sgn">-</span>{t}' if v < 0 else t


def hover_rect(p, k):
    return f'<rect class="hov" data-k="{k}" x="{p.x}" y="{p.y}" width="{p.w}" height="{p.h}"/><line id="xh{k}" y1="{p.y}" y2="{p.y + p.h}" stroke="#888" stroke-width="1" style="display:none;pointer-events:none"/>'


def title_block(c):
    L = c.L
    t = L["ytd_title"].format(y=c.end.year) if is_ytd(c.start, c.end) else L["range_title"].format(a=fdate(c.start), b=fdate(c.end))
    user = c.spec.get("title", {}).get(c.lang)
    sub = L["sub_total" if c.total else "sub"].format(base=fdate(c.base)) + (L["log"] if c.log else "")
    return f'<div class="band"><div class="t">{user or t}</div><div class="s">{sub}</div></div>'


def layout_lines(c):
    L, T, series, benches, allk = c.L, c.T, c.series, c.benches, c.allk
    lo, hi, ticks = y_range(allk, c.log)
    right, H1 = 146, 300
    p = Plot(44, 14, W - 44 - right, H1 - 14 - 30, lo, hi, c.base, c.end, c.log)
    g = [axes(c, p, ticks)]
    for s in benches[::-1] + series[::-1]:
        g.append(line(p, s, c.col[s.sym], 1.6 if s.is_bench else 2, c.dash(s)))
    ys = {s.sym: p.py(s.idx[-1]) for s in allk}
    adj = spread(list(ys.items()), 16, p.y + p.h)
    for s in allk:
        ex, ey = p.px(s.dates[-1]), ys[s.sym]
        if abs(adj[s.sym] - ey) > 4:
            g.append(f'<line x1="{ex + 4:.1f}" y1="{ey:.1f}" x2="{ex + 11:.1f}" y2="{adj[s.sym]:.1f}" stroke="{T["axis"]}" stroke-width="1"/>')
        g.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="3.5" fill="{c.col[s.sym]}" stroke="{T["ring"]}" stroke-width="2"/>')
        nm = c.bench_short(s) if s.is_bench else s.sym
        g.append(f'<text x="{ex + 14:.1f}" y="{adj[s.sym] + 4:.1f}" font-size="12" fill="{T["ink"]}"><tspan font-weight="700">{nm}</tspan>  {f1(s.ret, True)}%</text>')
    k = len(c.hov)
    c.add_hover(p, [(c.bench_short(s) if s.is_bench else s.sym, c.col[s.sym], s) for s in allk], f"s{k}")
    g.append(hover_rect(p, k))
    parts = [f'<svg id="s{k}" width="{W}" height="{H1}" font-family=\'{FONT}\'>{"".join(g)}</svg>']
    legend = "".join(f'<span class="lg">{swatch(c.col[s.sym], c.dash(s))}{c.bench_label(s) if s.is_bench else s.sym}</span>' for s in allk)
    parts.insert(0, f'<div class="legend">{legend}</div>')
    if c.dd_on:
        mn = min(s.mdd for s in allk)
        step = nice_ticks(mn * 1.08, 0, 4)
        dlo = min(step[0], mn * 1.08)
        H2 = 130
        q = Plot(44, 10, W - 44 - right, H2 - 10 - 28, dlo, 0, c.base, c.end)
        g2 = [axes(c, q, step, base=0)]
        for s in benches[::-1] + series[::-1]:
            da = f' stroke-dasharray="{c.dash(s)}"' if s.is_bench else ""
            g2.append(f'<path d="{q.path(s.dates, s.dd)}" fill="none" stroke="{c.col[s.sym]}" stroke-width="{1.4 if s.is_bench else 1.6}" stroke-linejoin="round"{da}/>')
        parts.append(f'<div class="ptitle">{L["dd_title"]}</div><svg width="{W}" height="{H2}" font-family=\'{FONT}\'>{"".join(g2)}</svg>')
    if c.spec.get("table", True):
        rows = []
        for s in sorted(allk, key=lambda s: -s.ret):
            nm = c.bench_label(s) if s.is_bench else c.name_of(s.sym)
            last = "NA" if (s.is_bench or c.total) else f"{s.close[-1]:,.2f}"
            rows.append(f'<tr class="{"bench" if s.is_bench else ""}"><td>{swatch(c.col[s.sym], c.dash(s), 18)}{nm}</td><td>{sg(s.ret)}</td><td>{s.vol:.1f}</td><td>{sg(s.mdd)}</td><td>{last}</td></tr>')
        rh = L["ret_ytd"] if is_ytd(c.start, c.end) else L["ret"]
        th = "".join(f"<th>{a}<br>{b}</th>" for a, b in [("", ""), rh, L["vol"], L["mdd"], L["last"]])
        parts.append('<table style="margin-top:6px"><colgroup><col style="width:39%"><col style="width:14%"><col style="width:16%"><col style="width:15%"><col style="width:16%"></colgroup>'
                     f'<thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table>')
    return "".join(parts)


def layout_multiples(c):
    L, T, series, benches, allk = c.L, c.T, c.series, c.benches, c.allk
    lo, hi, ticks = y_range(allk, c.log)
    if len(ticks) > 5:
        ticks = ticks[:: math.ceil(len(ticks) / 4)]
    cols = 3
    cw = W // cols
    price_h, dd_h = 108, 50
    ph = 46 + price_h + (10 + dd_h + 24 if c.dd_on else 26)
    order = sorted(series, key=lambda s: -s.ret)
    rows_n = math.ceil(len(order) / cols)
    mn = min(s.mdd for s in series)
    dd_ticks = nice_ticks(mn * 1.1, 0, 2)
    dlo = min(dd_ticks[0], mn * 1.1)
    out = []
    for n, s in enumerate(order):
        cx, cy = (n % cols) * cw, (n // cols) * ph
        p = Plot(cx + 38, cy + 46, cw - 38 - 14, price_h, lo, hi, c.base, c.end, c.log)
        g = [f'<text x="{cx + 10}" y="{cy + 20}" font-size="13" font-weight="700" fill="{T["stock"]}">{s.sym}</text>',
             f'<text x="{cx + cw - 14}" y="{cy + 20}" font-size="13" font-weight="600" text-anchor="end" fill="{T["ink"]}">{f1(s.ret, True)}%</text>']
        for t in ticks:
            y = p.py(t)
            g.append(f'<line x1="{p.x}" x2="{p.x + p.w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{T["axis"] if t == 100 else T["grid"]}"/>')
            g.append(f'<text x="{p.x - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="{T["muted"]}">{t:g}</text>')
        for i, b in enumerate(benches):
            g.append(f'<path d="{p.path(b.dates, b.idx)}" fill="none" stroke="{T["bench_multi"]}" stroke-width="1.5" stroke-dasharray="{DASHES[min(i, 1)]}"/>')
        g.append(f'<path d="{p.path(s.dates, s.idx)}" fill="none" stroke="{T["stock"]}" stroke-width="2" stroke-linejoin="round"/>')
        g.append(f'<circle cx="{p.px(s.dates[-1]):.1f}" cy="{p.py(s.idx[-1]):.1f}" r="3" fill="{T["stock"]}" stroke="{T["ring"]}" stroke-width="2"/>')
        k = len(c.hov)
        c.add_hover(p, [(s.sym, T["stock"], s)] + [(c.bench_short(b), T["bench_multi"], b) for b in benches], "sm")
        g.append(hover_rect(p, k))
        if c.dd_on:
            g.append(f'<text x="{cx + 10}" y="{cy + 36}" font-size="10.5" fill="{T["muted"]}">{L["mdd"][0]} {L["mdd"][1].replace(" (%)", "")} {f1(s.mdd)}%</text>')
        xbase = p.y + p.h
        if c.dd_on:
            q = Plot(cx + 38, p.y + p.h + 10, cw - 38 - 14, dd_h, dlo, 0, c.base, c.end)
            for t in dd_ticks:
                y = q.py(t)
                g.append(f'<line x1="{q.x}" x2="{q.x + q.w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{T["axis"] if t == 0 else T["grid"]}"/>')
                g.append(f'<text x="{q.x - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="{T["muted"]}">{t:g}</text>')
            pts = " ".join(f"{q.px(d):.1f},{q.py(v):.1f}" for d, v in zip(s.dates, s.dd))
            g.append(f'<polygon points="{q.px(s.dates[0]):.1f},{q.py(0):.1f} {pts} {q.px(s.dates[-1]):.1f},{q.py(0):.1f}" fill="{T["dd_fill"]}" opacity="{T["dd_op"]}"/>')
            g.append(f'<polyline points="{pts}" fill="none" stroke="{T["stock"]}" stroke-width="1.2" stroke-linejoin="round"/>')
            xbase = q.y + q.h
        xt = x_ticks(c.base, c.end, L)
        for d, lab in xt[:: max(1, math.ceil(len(xt) / 4))]:
            g.append(f'<text x="{p.px(d):.1f}" y="{xbase + 14}" text-anchor="middle" font-size="10" fill="{T["muted"]}">{lab}</text>')
        out.append("".join(g))
    Ht = ph * rows_n + 4
    dv = "".join(f'<line x1="0" x2="{W}" y1="{ph * r}" y2="{ph * r}" stroke="{T["rule"]}"/>' for r in range(1, rows_n))
    dv += "".join(f'<line x1="{cw * i}" x2="{cw * i}" y1="0" y2="{Ht}" stroke="{T["rule"]}"/>' for i in range(1, cols))
    legend = (f'<div class="legend" style="padding-bottom:4px"><span class="lg">{swatch(T["stock"])}{L["stock"]}</span>'
              + "".join(f'<span class="lg">{swatch(T["bench_multi"], DASHES[min(i, 1)])}{c.bench_label(b)}</span>' for i, b in enumerate(benches))
              + f'<span style="color:{T["muted"]}">{L["same"]}</span>'
              + (f'<span style="color:{T["muted"]}">{L["dd_title"]}</span>' if c.dd_on else "") + "</div>")
    return legend + f'<svg id="sm" width="{W}" height="{Ht}" font-family=\'{FONT}\'>{dv}{"".join(out)}</svg>'


def footnote(c):
    L = c.L
    srcs = []
    for s in c.allk:
        raw = s.source or c.d["series"][s.sym].get("source", "")
        t = ZH_SRC.get(raw, raw) if c.lang == "zh" else raw
        if t and t not in srcs:
            srcs.append(t)
    got = dt.datetime.fromisoformat(c.d["fetched_at"]).date()
    etf = [b.sym for b in c.benches if c.d["series"][b.sym].get("class") == "etf"]
    bench = ""
    if c.benches:
        bench = (L["bench_etf"].format(b=("、" if c.lang == "zh" else ", ").join(etf)) if etf else "") + L["bench_idx"]
    basis = L["basis_total"] if c.total else L["basis_price"]
    sep = "；" if c.lang == "zh" else "; "
    return c.spec.get("note", {}).get(c.lang, "") + L["foot"].format(src=sep.join(srcs), end=fdate(c.end), got=fdate(got), base=fdate(c.base), basis=basis, bench=bench)


HOVER_JS = r"""
(function(){
var P=__DATA__,tip=document.getElementById('tip'),wrap=document.getElementById('wrap'),M=__MONTHS__,F=__FMT__;
function near(a,x){var lo=0,hi=a.length-1;while(hi-lo>1){var m=(lo+hi)>>1;if(a[m]<x)lo=m;else hi=m;}return Math.abs(a[lo]-x)<=Math.abs(a[hi]-x)?lo:hi;}
function fmtd(iso){var p=iso.split('-');return F.replace('{y}',p[0]).replace('{m}',+p[1]).replace('{d}',+p[2]);}
Array.prototype.forEach.call(document.querySelectorAll('.hov'),function(r){
 var k=+r.getAttribute('data-k'),p=P[k],svg=r.ownerSVGElement,xh=svg.querySelector('#xh'+k);
 r.addEventListener('mousemove',function(e){
  var b=svg.getBoundingClientRect(),x=e.clientX-b.left,i=near(p.xs,x),d=p.dates[i],h='<b>'+fmtd(d)+'</b>';
  p.rows.forEach(function(w){var v=w.m[d];if(v!==undefined){h+='<br><i style="background:'+w.c+'"></i>'+w.n+' '+v.toFixed(1)+' ('+(v>=100?'+':'')+(v-100).toFixed(1)+'%)';}});
  tip.innerHTML=h;tip.style.display='block';xh.setAttribute('x1',p.xs[i]);xh.setAttribute('x2',p.xs[i]);xh.style.display='';
  var wb=wrap.getBoundingClientRect(),tx=e.clientX-wb.left+14,ty=e.clientY-wb.top+10;
  if(tx+tip.offsetWidth>wb.width-4)tx=e.clientX-wb.left-tip.offsetWidth-14;
  tip.style.left=tx+'px';tip.style.top=ty+'px';});
 r.addEventListener('mouseleave',function(){tip.style.display='none';xh.style.display='none';});
});})();
"""


def build_html(spec, d, series, benches, base, end, start, lang, theme="light"):
    c = Ctx(spec, d, series, benches, base, end, start, lang, theme)
    mode = spec.get("layout", "auto")
    if mode == "auto":
        mode = "lines" if len(series) <= MAX_LINES else "multiples"
    if mode == "lines" and len(series) > MAX_LINES:
        sys.exit(f"error: lines layout supports at most {MAX_LINES} symbols; use layout=multiples")
    body = layout_lines(c) if mode == "lines" else layout_multiples(c)
    data = json.dumps(c.hov, separators=(",", ":")).replace("</", "<\\/")
    js = HOVER_JS.replace("__DATA__", data).replace("__MONTHS__", json.dumps(c.L["months"], ensure_ascii=False)).replace("__FMT__", json.dumps(c.L["tip_d"]))
    return (f'<!doctype html><html lang="{c.L["lang"]}"><head><meta charset="utf-8"><title>Price performance</title><style>{c.css()}</style></head>'
            f'<body><div id="wrap"><div class="box">{title_block(c)}{body}</div><div class="foot">{footnote(c)}</div><div id="tip"></div></div><script>{js}</script></body></html>')


def main():
    ap = argparse.ArgumentParser(description="Render a Schwab-style price-performance chart from fetch_prices.py data.")
    ap.add_argument("spec")
    ap.add_argument("prefix")
    ap.add_argument("--langs", default="en,zh")
    ap.add_argument("--no-png", action="store_true", help="write HTML only (no Playwright needed)")
    ap.add_argument("--pdf", action="store_true", help="also write a vector PDF")
    ap.add_argument("--scale", type=float, default=2, help="PNG pixel density (default 2; use 3 for print)")
    ap.add_argument("--theme", choices=sorted(THEMES), default="light", help="light (default) or dark")
    a = ap.parse_args()
    sp = Path(a.spec)
    spec = json.loads(sp.read_text(encoding="utf-8"))
    d, series, benches, base, end, start, warnings = load(spec, sp.parent)
    for w in warnings:
        print("warning:", w, file=sys.stderr)
    langs = [x.strip() for x in a.langs.split(",")]
    Path(a.prefix).parent.mkdir(parents=True, exist_ok=True)
    htmls = {l: build_html(spec, d, series, benches, base, end, start, l, a.theme) for l in langs}
    for l, h in htmls.items():
        Path(f"{a.prefix}_{l}.html").write_text(h, encoding="utf-8")
        print(f"wrote {a.prefix}_{l}.html")
    if not a.no_png or a.pdf:
        render_files(htmls, a.prefix, a.scale, png=not a.no_png, pdf=a.pdf)
    print("base date:", base, "| end:", end, "| " + ", ".join(f"{s.sym} {f1(s.ret, True)}%" for s in series + benches))


if __name__ == "__main__":
    main()
