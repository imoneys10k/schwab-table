"""Render a Schwab-style price-performance chart (EN + ZH) from fetch_prices.py output.

Usage: python3 render_chart.py spec.json OUT_PREFIX [--langs en,zh] [--no-png] [--scale 2]

Spec:
{
  "data": "data/neural9.json",                 # output of fetch_prices.py
  "symbols": ["MU", "NVDA"],                    # optional subset / order (default: all non-benchmark series)
  "names": {"MU": {"en": "Micron Technology Inc", "zh": "美光科技"}},
  "benchmark_name": {"en": "S&P 500 (SPY)", "zh": "标普 500 (SPY)"},
  "layout": "auto",                             # auto | lines | multiples   (auto: <=5 symbols lines, else multiples)
  "y_scale": "auto",                            # auto (log when the range is wide) | linear | log
  "drawdown": true,                             # add a drawdown-from-peak panel
  "table": true,                                # lines layout: summary table under the chart
  "start": "2026-01-01", "end": "2026-10-02",   # optional; default = the fetched range. start = base date: indexed to 100 at the last close on or before it
  "title": {"en": "...", "zh": "..."},          # optional
  "note": {"en": "...", "zh": "..."}            # optional text put at the start of the footnote (e.g. "Hypothetical example")
}
"""
import argparse
import asyncio
import bisect
import datetime as dt
import json
import math
import sys
from pathlib import Path

from fonts import font_face_css

FONT = ('"Inter","Helvetica Neue",Helvetica,Arial,"Noto Sans CJK SC","Source Han Sans SC","PingFang SC","Microsoft YaHei",sans-serif')
NAVY, BAND, GRID, AXIS, MUTED, INK = "#1B2A4A", "#ACDCEC", "#E4E4E4", "#9A9A9A", "#6B6B6B", "#2B2B2B"
BENCH = "#595959"
SER = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]  # validated categorical slots 1-5, fixed order
MAX_SYMBOLS = 9
MAX_LINES = 5

S = {
    "en": {
        "ytd_title": "{y} YTD Price Performance", "range_title": "Price Performance, {a} – {b}",
        "sub": "Indexed to 100 at {base} close · Daily close", "log": " · Log scale",
        "ret_ytd": ("YTD", "return (%)"), "ret": ("Period", "return (%)"), "vol": ("Ann.", "volatility (%)"),
        "mdd": ("Max", "drawdown (%)"), "last": ("Last", "price ($)"), "bench": "Benchmark",
        "dd_title": "Drawdown from peak (%)", "same": "Same scale in every panel", "stock": "Stock",
        "foot": ("Source: {src}, as of {end}; retrieved {got}. Indexed to 100 at the {base} close. Returns are price returns (excluding dividends) "
                 "computed from official closing prices. Annualized volatility is the standard deviation of daily price returns × √252; maximum drawdown is "
                 "the largest peak-to-trough decline in closing price over the period. {bench}All corporate names and market data shown above are for "
                 "illustrative purposes only and are not a recommendation, offer to sell, or a solicitation of an offer to buy any security. "
                 "<b>Past performance is no guarantee of future results.</b>"),
        "bench_etf": "{b} is an exchange-traded fund used here as a proxy for its index; it is not the index itself and cannot replicate it exactly. ",
        "bench_idx": "Indexes are unmanaged, do not incur management fees, costs and expenses and cannot be invested in directly. ",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], "lang": "en",
    },
    "zh": {
        "ytd_title": "{y} 年股价表现（年初至今）", "range_title": "股价表现，{a} – {b}",
        "sub": "以 {base} 收盘价为 100 · 日收盘价", "log": " · 对数刻度",
        "ret_ytd": ("年初", "至今 (%)"), "ret": ("区间", "涨跌幅 (%)"), "vol": ("年化", "波动率 (%)"),
        "mdd": ("最大", "回撤 (%)"), "last": ("最新", "收盘价 ($)"), "bench": "基准",
        "dd_title": "距前高回撤 (%)", "same": "各图纵轴一致", "stock": "个股",
        "foot": ("资料来源：{src}，截至 {end}，数据获取于 {got}。以 {base} 收盘价为 100。回报为由官方收盘价计算的价格回报（不含股息）。"
                 "年化波动率为日价格回报标准差 × √252；最大回撤为区间内收盘价自前高的最大跌幅。{bench}"
                 "以上公司名称及市场数据仅作说明用途，不构成任何证券的推荐、出售要约或购买要约邀请。<b>过往业绩不代表未来表现。</b>"),
        "bench_etf": "{b} 为交易所交易基金，此处仅用作其对应指数的替代，并非指数本身，也无法完全复制指数。",
        "bench_idx": "指数不受管理，不产生管理费及其他费用，且不可直接投资。",
        "months": ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"], "lang": "zh-CN",
    },
}


def fdate(d):
    return f"{d.month}/{d.day}/{d.year}"


def f1(v, sign=False):
    t = f"{abs(v):.1f}"
    return ("-" if v < 0 else ("+" if sign else "")) + t


# ---- data ---------------------------------------------------------------------
class Series:
    def __init__(self, sym, raw_pts, base, end, is_bench=False):
        self.sym, self.is_bench = sym, is_bench
        pts = [(dt.date.fromisoformat(d), c) for d, c in raw_pts]
        i = bisect.bisect_right([d for d, _ in pts], base) - 1
        if i < 0 or (base - pts[i][0]).days > 7:
            raise ValueError(f"{sym}: no close on or within 7 days before the base date {base}")
        self.base_date, base_close = pts[i]
        pts = [(d, c) for d, c in pts[i:] if d <= end]
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
    end = dt.date.fromisoformat(spec["end"]) if spec.get("end") else dt.date.fromisoformat(d["end"])
    start = dt.date.fromisoformat(spec["start"]) if spec.get("start") else dt.date.fromisoformat(d["start"])
    allpts = {k: v for k, v in d["series"].items()}
    last_close = max(dt.date.fromisoformat(v["points"][-1][0]) for v in allpts.values())
    end = min(end, last_close)
    syms = spec.get("symbols") or [k for k, v in allpts.items() if not v["benchmark"]]
    bench = d.get("benchmark")
    warnings, series = [], []
    for s in syms:
        if s not in allpts:
            warnings.append(f"{s}: not in data file, left out")
            continue
        try:
            series.append(Series(s, allpts[s]["points"], start, end))
        except ValueError as e:
            warnings.append(f"{e}; left out")
    if not series:
        sys.exit("error: no usable series")
    if len(series) > MAX_SYMBOLS:
        warnings.append(f"{len(series)} symbols given, keeping the first {MAX_SYMBOLS}")
        series = series[:MAX_SYMBOLS]
    bs = None
    if bench and bench in allpts:
        try:
            bs = Series(bench, allpts[bench]["points"], start, end, True)
        except ValueError as e:
            warnings.append(f"benchmark {e}; left out")
    base = series[0].base_date
    if any(x.base_date != base for x in series) or (bs and bs.base_date != base):
        warnings.append("base dates differ between series (a holiday gap?): " + ", ".join(f"{x.sym}={x.base_date}" for x in series + ([bs] if bs else [])))
    return d, series, bs, base, end, start, warnings


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
    items = sorted(items, key=lambda kv: kv[1])
    ys = [y for _, y in items]
    for i in range(1, len(ys)):
        ys[i] = max(ys[i], ys[i - 1] + gap)
    over = ys[-1] - hi
    if over > 0:
        ys = [y - over for y in ys]
    return {k: y for (k, _), y in zip(items, ys)}


# ---- svg building blocks ---------------------------------------------------------
def axes(p, ticks, L, xlabels=True, fmt=lambda v: f"{v:g}", fs=11, base=100):
    g = []
    for t in ticks:
        y = p.py(t) if t > 0 or not p.log else p.py(p.lo)
        g.append(f'<line x1="{p.x}" x2="{p.x + p.w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{AXIS if t == base else GRID}"/>')
        g.append(f'<text x="{p.x - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="{fs}" fill="{MUTED}">{fmt(t)}</text>')
    if xlabels:
        for d, lab in x_ticks(p.d0, p.d1, L):
            x = p.px(d)
            g.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{p.y + p.h}" y2="{p.y + p.h + 4}" stroke="{AXIS}"/>')
            g.append(f'<text x="{x:.1f}" y="{p.y + p.h + 17}" text-anchor="middle" font-size="{fs}" fill="{MUTED}">{lab}</text>')
    g.append(f'<line x1="{p.x}" x2="{p.x + p.w}" y1="{p.y + p.h}" y2="{p.y + p.h}" stroke="{AXIS}"/>')
    return "".join(g)


def line(p, s, col, w=2, dash=""):
    return (f'<path d="{p.path(s.dates, s.idx)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" '
            f'stroke-linecap="round"{(" stroke-dasharray=" + chr(34) + dash + chr(34)) if dash else ""}/>')


def swatch(col, dash=False, w=22):
    d = ' stroke-dasharray="4 3"' if dash else ""
    return f'<svg width="{w}" height="8"><line x1="0" x2="{w}" y1="4" y2="4" stroke="{col}" stroke-width="2.5"{d}/></svg>'


# ---- page ---------------------------------------------------------------------------
CSS = font_face_css() + f"""
body{{margin:0;background:#fff;font-family:{FONT};-webkit-font-smoothing:antialiased}}
#wrap{{width:736px;padding:12px;background:#fff}}
.box{{border:1px solid #D0D0D0}}
.band{{background:{BAND};color:{NAVY};text-align:center;padding:9px 10px 8px}}
.band .t{{font-size:15px;font-weight:700}} .band .s{{font-size:12.5px;font-weight:500;margin-top:2px}}
.legend{{padding:8px 12px 0;font-size:12.5px;color:{INK};display:flex;gap:16px;flex-wrap:wrap;align-items:center}}
.lg{{display:inline-flex;align-items:center;gap:6px}}
.ptitle{{padding:6px 12px 0;font-size:12px;font-weight:700;color:{NAVY}}}
.foot{{margin-top:7px;font-size:10px;color:#6B6B6B;line-height:1.4}} .foot b{{font-weight:600;color:#555}}
table{{width:100%;border-collapse:collapse;table-layout:fixed;font-size:13px;color:#595959}}
th{{background:{BAND};color:{NAVY};font-weight:600;text-align:right;padding:5px 12px 5px 8px;font-size:12.5px;line-height:1.25;vertical-align:bottom}}
td{{text-align:right;padding:0 12px 0 8px;height:25px;border-top:1px solid #D9D9D9;font-feature-settings:"tnum" 1;white-space:nowrap}}
th:first-child,td:first-child{{text-align:left;padding-left:12px}}
td svg{{vertical-align:middle;margin-right:7px}}
tr.bench td{{color:{INK};font-weight:600}}
.sgn{{font-feature-settings:"tnum" 0}}
"""

W = 734  # inner width of the box


def title_block(L, base, start, end, log, ytd):
    if ytd:
        t = L["ytd_title"].format(y=end.year)
    else:
        t = L["range_title"].format(a=fdate(start), b=fdate(end))
    sub = L["sub"].format(base=fdate(base)) + (L["log"] if log else "")
    return f'<div class="band"><div class="t">{t}</div><div class="s">{sub}</div></div>'


def name_of(spec, sym, lang):
    n = spec.get("names", {}).get(sym, {}).get(lang)
    return f"{n} ({sym})" if n else sym


def bench_label(spec, lang, bs):
    n = spec.get("benchmark_name", {}).get(lang)
    return n or (bs.sym if bs else "")


def layout_lines(spec, L, lang, series, bs, base, end, start, log, dd_on, table_on):
    allk = series + ([bs] if bs else [])
    col = {s.sym: SER[i] for i, s in enumerate(series)}
    if bs:
        col[bs.sym] = BENCH
    lo, hi, ticks = y_range(allk, log)
    right = 146
    H1 = 300
    p = Plot(44, 14, W - 44 - right, H1 - 14 - 30, lo, hi, base, end, log)
    g = [axes(p, ticks, L)]
    for s in ([bs] if bs else []) + series[::-1]:
        g.append(line(p, s, col[s.sym], 1.6 if s.is_bench else 2, "5 4" if s.is_bench else ""))
    ys = {s.sym: p.py(s.idx[-1]) for s in allk}
    adj = spread(list(ys.items()), 16, p.y + p.h)
    for s in allk:
        ex, ey = p.px(s.dates[-1]), ys[s.sym]
        if abs(adj[s.sym] - ey) > 4:
            g.append(f'<line x1="{ex + 4:.1f}" y1="{ey:.1f}" x2="{ex + 11:.1f}" y2="{adj[s.sym]:.1f}" stroke="{AXIS}" stroke-width="1"/>')
        g.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="3.5" fill="{col[s.sym]}" stroke="#fff" stroke-width="2"/>')
        nm = s.sym
        if s.is_bench:
            nm = bench_label(spec, lang, bs).split(" (")[0]
            if len(nm) > 10:
                nm = L["bench"]
        g.append(f'<text x="{ex + 14:.1f}" y="{adj[s.sym] + 4:.1f}" font-size="12" fill="{INK}"><tspan font-weight="700">{nm}</tspan>  {f1(s.ret, True)}%</text>')
    parts = [f'<svg width="{W}" height="{H1}" font-family=\'{FONT}\'>{"".join(g)}</svg>']
    legend = "".join(f'<span class="lg">{swatch(col[s.sym], s.is_bench)}{bench_label(spec, lang, bs) if s.is_bench else s.sym}</span>' for s in allk)
    parts.insert(0, f'<div class="legend">{legend}</div>')
    if dd_on:
        mn = min(s.mdd for s in allk)
        step = nice_ticks(mn * 1.08, 0, 4)
        dlo = min(step[0], mn * 1.08)
        H2 = 130
        q = Plot(44, 10, W - 44 - right, H2 - 10 - 28, dlo, 0, base, end)
        g2 = [axes(q, step, L, fmt=lambda v: f"{v:g}", base=0)]
        for s in ([bs] if bs else []) + series[::-1]:
            dash = ' stroke-dasharray="5 4"' if s.is_bench else ""
            g2.append(f'<path d="{q.path(s.dates, s.dd)}" fill="none" stroke="{col[s.sym]}" stroke-width="{1.4 if s.is_bench else 1.6}" stroke-linejoin="round"{dash}/>')
        parts.append(f'<div class="ptitle">{L["dd_title"]}</div><svg width="{W}" height="{H2}" font-family=\'{FONT}\'>{"".join(g2)}</svg>')
    if table_on:
        rows = []
        for s in sorted(allk, key=lambda s: -s.ret):
            nm = bench_label(spec, lang, bs) if s.is_bench else name_of(spec, s.sym, lang)
            last = "NA" if s.is_bench else f"{s.close[-1]:,.2f}"
            rows.append(f'<tr class="{"bench" if s.is_bench else ""}"><td>{swatch(col[s.sym], s.is_bench, 18)}{nm}</td><td>{sg(s.ret)}</td><td>{s.vol:.1f}</td><td>{sg(s.mdd)}</td><td>{last}</td></tr>')
        rh = L["ret_ytd"] if is_ytd(start, end) else L["ret"]
        th = "".join(f"<th>{a}<br>{b}</th>" for a, b in [("", ""), rh, L["vol"], L["mdd"], L["last"]])
        parts.append('<table style="margin-top:6px"><colgroup><col style="width:39%"><col style="width:14%"><col style="width:16%"><col style="width:15%"><col style="width:16%"></colgroup>'
                     f'<thead><tr>{th}</tr></thead><tbody>{"".join(rows)}</tbody></table>')
    return "".join(parts)


def sg(v):
    t = f"{abs(v):.1f}"
    return f'<span class="sgn">-</span>{t}' if v < 0 else t


def is_ytd(start, end):
    return start == dt.date(end.year, 1, 1)


def layout_multiples(spec, L, lang, series, bs, base, end, start, log, dd_on):
    allk = series + ([bs] if bs else [])
    lo, hi, ticks = y_range(allk, log)
    if len(ticks) > 5:
        ticks = ticks[:: math.ceil(len(ticks) / 4)]
    cols = 3
    cw = W // cols
    price_h, dd_h = 108, 50
    ph = 46 + price_h + (10 + dd_h + 24 if dd_on else 26)
    order = sorted(series, key=lambda s: -s.ret)
    rows_n = math.ceil(len(order) / cols)
    mn = min(s.mdd for s in series)
    dd_ticks = nice_ticks(mn * 1.1, 0, 2)
    dlo = min(dd_ticks[0], mn * 1.1)
    out = []
    for n, s in enumerate(order):
        cx, cy = (n % cols) * cw, (n // cols) * ph
        p = Plot(cx + 38, cy + 46, cw - 38 - 14, price_h, lo, hi, base, end, log)
        g = [f'<text x="{cx + 10}" y="{cy + 20}" font-size="13" font-weight="700" fill="{NAVY}">{s.sym}</text>',
             f'<text x="{cx + cw - 14}" y="{cy + 20}" font-size="13" font-weight="600" text-anchor="end" fill="{INK}">{f1(s.ret, True)}%</text>']
        for t in ticks:
            y = p.py(t)
            g.append(f'<line x1="{p.x}" x2="{p.x + p.w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{AXIS if t == 100 else GRID}"/>')
            g.append(f'<text x="{p.x - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="{MUTED}">{t:g}</text>')
        if bs:
            g.append(f'<path d="{p.path(bs.dates, bs.idx)}" fill="none" stroke="#B5B5B5" stroke-width="1.5" stroke-dasharray="4 3"/>')
        g.append(f'<path d="{p.path(s.dates, s.idx)}" fill="none" stroke="{NAVY}" stroke-width="2" stroke-linejoin="round"/>')
        g.append(f'<circle cx="{p.px(s.dates[-1]):.1f}" cy="{p.py(s.idx[-1]):.1f}" r="3" fill="{NAVY}" stroke="#fff" stroke-width="2"/>')
        if dd_on:
            g.append(f'<text x="{cx + 10}" y="{cy + 36}" font-size="10.5" fill="{MUTED}">{L["mdd"][0]} {L["mdd"][1].replace(" (%)", "")} {f1(s.mdd)}%</text>')
        xbase = p.y + p.h
        if dd_on:
            q = Plot(cx + 38, p.y + p.h + 10, cw - 38 - 14, dd_h, dlo, 0, base, end)
            for t in dd_ticks:
                y = q.py(t)
                g.append(f'<line x1="{q.x}" x2="{q.x + q.w}" y1="{y:.1f}" y2="{y:.1f}" stroke="{AXIS if t == 0 else GRID}"/>')
                g.append(f'<text x="{q.x - 6}" y="{y + 4:.1f}" text-anchor="end" font-size="10" fill="{MUTED}">{t:g}</text>')
            pts = " ".join(f"{q.px(d):.1f},{q.py(v):.1f}" for d, v in zip(s.dates, s.dd))
            g.append(f'<polygon points="{q.px(s.dates[0]):.1f},{q.py(0):.1f} {pts} {q.px(s.dates[-1]):.1f},{q.py(0):.1f}" fill="{BAND}" opacity="0.65"/>')
            g.append(f'<polyline points="{pts}" fill="none" stroke="{NAVY}" stroke-width="1.2" stroke-linejoin="round"/>')
            xbase = q.y + q.h
        xt = x_ticks(base, end, L)
        keep = xt[:: max(1, math.ceil(len(xt) / 4))]
        for d, lab in keep:
            g.append(f'<text x="{p.px(d):.1f}" y="{xbase + 14}" text-anchor="middle" font-size="10" fill="{MUTED}">{lab}</text>')
        out.append("".join(g))
    Ht = ph * rows_n + 4
    dv = "".join(f'<line x1="0" x2="{W}" y1="{ph * r}" y2="{ph * r}" stroke="#D9D9D9"/>' for r in range(1, rows_n))
    dv += "".join(f'<line x1="{cw * i}" x2="{cw * i}" y1="0" y2="{Ht}" stroke="#D9D9D9"/>' for i in range(1, cols))
    legend = (f'<div class="legend" style="padding-bottom:4px"><span class="lg">{swatch(NAVY)}{L["stock"]}</span>'
              + (f'<span class="lg">{swatch("#B5B5B5", True)}{bench_label(spec, lang, bs)}</span>' if bs else "")
              + f'<span style="color:{MUTED}">{L["same"]}</span>'
              + (f'<span style="color:{MUTED}">{L["dd_title"]}</span>' if dd_on else "") + "</div>")
    return legend + f'<svg width="{W}" height="{Ht}" font-family=\'{FONT}\'>{dv}{"".join(out)}</svg>'


def footnote(L, d, base, end, bs, spec, lang):
    zh_src = {"Nasdaq (official closing prices, split-adjusted)": "纳斯达克（官方收盘价，已按拆股调整）",
              "S&P 500 (S&P Dow Jones Indices, via FRED)": "标普 500（标普道琼斯指数公司，经 FRED 转载）",
              "Nasdaq Composite (Nasdaq Global Indexes, via FRED)": "纳斯达克综合指数（Nasdaq Global Indexes，经 FRED 转载）",
              "Synthetic sample data (not real market data)": "虚构示例数据（非真实行情）"}
    srcs = []
    for v in d["series"].values():
        t = zh_src.get(v["source"], v["source"]) if lang == "zh" else v["source"]
        if t not in srcs:
            srcs.append(t)
    got = dt.datetime.fromisoformat(d["fetched_at"]).date()
    bench = ""
    if bs:
        cls = d["series"][bs.sym]["class"]
        bench = L["bench_etf"].format(b=bs.sym) if cls == "etf" else L["bench_idx"]
        if cls == "etf":
            bench += L["bench_idx"]
    return spec.get("note", {}).get(lang, "") + L["foot"].format(src=("；" if lang == "zh" else "; ").join(srcs), end=fdate(end), got=fdate(got), base=fdate(base), bench=bench)


def use_log(spec, series, bs):
    mode = spec.get("y_scale", "auto")
    if mode != "auto":
        return mode == "log"
    allk = series + ([bs] if bs else [])
    return max(max(s.idx) for s in allk) / min(min(s.idx) for s in allk) > 3  # a >3x spread flattens everything else on a linear axis


def build_html(spec, d, series, bs, base, end, start, lang):
    L = S[lang]
    log = use_log(spec, series, bs)
    dd_on = bool(spec.get("drawdown", True))
    mode = spec.get("layout", "auto")
    if mode == "auto":
        mode = "lines" if len(series) <= MAX_LINES else "multiples"
    if mode == "lines" and len(series) > MAX_LINES:
        sys.exit(f"error: lines layout supports at most {MAX_LINES} symbols; use layout=multiples")
    body = (layout_lines(spec, L, lang, series, bs, base, end, start, log, dd_on, spec.get("table", True)) if mode == "lines"
            else layout_multiples(spec, L, lang, series, bs, base, end, start, log, dd_on))
    t = spec.get("title", {}).get(lang)
    band = title_block(L, base, start, end, log, is_ytd(start, end))
    if t:
        band = band.replace(band.split('<div class="t">')[1].split("</div>")[0], t, 1)
    return (f'<!doctype html><html lang="{L["lang"]}"><head><meta charset="utf-8"><title>Price performance</title><style>{CSS}</style></head>'
            f'<body><div id="wrap"><div class="box">{band}{body}</div><div class="foot">{footnote(L, d, base, end, bs, spec, lang)}</div></div></body></html>')


async def render_png(htmls, prefix, scale=2):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        sys.exit("error: playwright is not installed (pip install playwright && playwright install chromium), or pass --no-png")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        for lang, html in htmls.items():
            pg = await b.new_page(device_scale_factor=scale, viewport={"width": 800, "height": 700})
            await pg.set_content(html)
            await pg.evaluate("document.fonts.ready")
            await pg.locator("#wrap").screenshot(path=f"{prefix}_{lang}.png")
            await pg.close()
        await b.close()


def main():
    ap = argparse.ArgumentParser(description="Render a Schwab-style price-performance chart from fetch_prices.py data.")
    ap.add_argument("spec")
    ap.add_argument("prefix")
    ap.add_argument("--langs", default="en,zh")
    ap.add_argument("--no-png", action="store_true")
    ap.add_argument("--scale", type=float, default=2, help="PNG pixel density (default 2; use 3 for print)")
    a = ap.parse_args()
    sp = Path(a.spec)
    spec = json.loads(sp.read_text(encoding="utf-8"))
    d, series, bs, base, end, start, warnings = load(spec, sp.parent)
    for w in warnings:
        print("warning:", w, file=sys.stderr)
    langs = [l.strip() for l in a.langs.split(",")]
    Path(a.prefix).parent.mkdir(parents=True, exist_ok=True)
    htmls = {l: build_html(spec, d, series, bs, base, end, start, l) for l in langs}
    for l, h in htmls.items():
        Path(f"{a.prefix}_{l}.html").write_text(h, encoding="utf-8")
        print(f"wrote {a.prefix}_{l}.html")
    if not a.no_png:
        asyncio.run(render_png(htmls, a.prefix, a.scale))
        for l in htmls:
            print(f"wrote {a.prefix}_{l}.png")
    print("base date:", base, "| end:", end, "| " + ", ".join(f"{s.sym} {f1(s.ret, True)}%" for s in series + ([bs] if bs else [])))


if __name__ == "__main__":
    main()
