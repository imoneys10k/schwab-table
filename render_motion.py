"""Animated charts and tables that settle on the exact static image.

Usage: python3 render_motion.py INPUT.json OUT_PREFIX [--formats gif,mp4,live] [--langs en,zh] [--theme light|dark]
                                [--draw 3.6] [--hold 1.6] [--fps 30] [--scale 2] [--gif-width 760]
       table input:    [--style schwab|morgan|blackstone|ibkr]
       holdings input: [--top 13] [--mode exposure|lines] [--by holding|name|sector] [--merge-classes] [--names names.json]

INPUT is any of the three inputs the static renderers take, recognised by its content:
  price chart  render_chart.py spec ("data" key)            the lines draw left to right; labels, table and date follow the cursor
  table        render_table.py spec ("langs" + "rows")      rows come in one after another and their numbers count up
  holdings     fetch_holdings.py output ("holdings" list)   bars grow one after another, weights and the cumulative column count up
Per language it writes:
  gif   OUT_PREFIX_{lang}.gif                       looping GIF (chat apps, X, web pages)
  mp4   OUT_PREFIX_{lang}.mp4                       H.264 video (Xiaohongshu, X, slides)
  live  OUT_PREFIX_{lang}_live.jpg + _live.mov      an Apple Live Photo pair: both carry the same content identifier, so AirDropping
                                                    both to an iPhone, or importing both into Photos, gives one Live Photo
The last frame is pixel-identical to the PNG of the matching static renderer. Needs Playwright + Chromium (like the other renderers) and ffmpeg.
The Live Photo metadata is written here in plain Python (no exiftool, works on any OS).
"""
import argparse
import asyncio
import json
import math
import shutil
import struct
import subprocess
import sys
import tempfile
import uuid
from html import escape
from pathlib import Path

import render_chart as rc
import render_holdings as rh
import render_table as rt
from institutional_tables import STYLES
from localization import traditional
from render_common import THEMES, reexec_in_venv

FORMATS = ("gif", "mp4", "live")
KINDS = ("chart", "table", "holdings")
LIVE_KEY = b"com.apple.quicktime.content.identifier"

# window.__frame(f, settle): f = how much of the period is drawn (0..1); settle = 0..1 cross-fade from the moving overlay
# (head dots, travelling labels, cursor, live table values) to the untouched static chart.
FRAME_JS = r"""
(() => {
const D = __DATA__;
const NS = 'http://www.w3.org/2000/svg';
const box = document.querySelector('.box');
const svgs = [...box.children].filter(e => e.tagName.toLowerCase() === 'svg');
const tip = document.getElementById('tip'); if (tip) tip.style.display = 'none';
const el = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (parent) parent.appendChild(e); return e; };
const f1 = (v, sign) => (v < 0 ? '-' : (sign ? '+' : '')) + Math.abs(v).toFixed(1);
const sg = v => v < 0 ? '<span class="sgn">-</span>' + Math.abs(v).toFixed(1) : v.toFixed(1);
const money = v => v.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
const fmtDate = s => { const [y, m, d] = s.split('-').map(Number); return D.lang === 'zh' ? `${y}年${m}月${d}日` : `${D.months[m - 1]} ${d}, ${y}`; };
const lerp = (a, k) => { const i = Math.floor(k), u = k - i; return i + 1 < a.length ? a[i] + u * (a[i + 1] - a[i]) : a[a.length - 1]; };

// running max drawdown and volatility, so the table can show values "as of the cursor"
for (const s of Object.values(D.series)) {
  s.mddRun = []; s.volRun = [];
  let mn = 0, n = 0, sum = 0, sq = 0;
  s.idx.forEach((v, k) => {
    mn = Math.min(mn, s.dd[k]); s.mddRun.push(mn);
    if (k > 0) { const r = v / s.idx[k - 1] - 1; n++; sum += r; sq += r * r; }
    s.volRun.push(n > 1 ? Math.sqrt(Math.max(sq - sum * sum / n, 0) / (n - 1)) * Math.sqrt(252) * 100 : 0);
  });
}

// vertices of a path / polyline / polygon as drawn ("M x,y L x,y ..." or "x,y x,y ...")
const verts = node => {
  const raw = node.getAttribute(node.tagName === 'path' ? 'd' : 'points');
  const nums = raw.replace(/[ML]/g, ' ').trim().split(/[\s,]+/).map(Number), out = [];
  for (let i = 0; i + 1 < nums.length; i += 2) out.push([nums[i], nums[i + 1]]);
  return out;
};
// point at horizontal fraction f of a series' own x-span; k = fractional index into its data
const at = (v, f) => {
  const x = v[0][0] + f * (v[v.length - 1][0] - v[0][0]);
  let lo = 0, hi = v.length - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (v[m][0] <= x) lo = m; else hi = m; }
  const span = v[hi][0] - v[lo][0], u = span > 0 ? Math.min(Math.max((x - v[lo][0]) / span, 0), 1) : 0;
  return {x, y: v[lo][1] + u * (v[hi][1] - v[lo][1]), k: lo + u * (hi - lo)};
};

let clipN = 0;
const reveal = [];
const clip = (svg, node) => {
  let defs = svg.querySelector('defs');
  if (!defs) { defs = el('defs', {}); svg.insertBefore(defs, svg.firstChild); }
  const id = 'mv' + (clipN++), v = verts(node);
  const rect = el('rect', {x: v[0][0] - 6, y: -50, width: 0, height: 5000}, el('clipPath', {id}, defs));
  node.setAttribute('clip-path', `url(#${id})`);
  reveal.push({rect, v});
};
// plot area from its horizontal gridlines (the bottom one is the x-axis)
const plotBox = svg => {
  const g = [...svg.querySelectorAll('line')].filter(l => l.getAttribute('y1') === l.getAttribute('y2') && +l.getAttribute('x2') - +l.getAttribute('x1') > 100);
  const ys = g.map(l => +l.getAttribute('y1'));
  return {y0: Math.min(...ys), y1: Math.max(...ys), x0: +g[0].getAttribute('x1'), x1: +g[0].getAttribute('x2')};
};

const statics = [], heads = [], layers = [], cursors = [];
let labels = null, dateTag = null;
const head = (layer, node, sym, color, big) => {
  const h = {layer, v: verts(node), sym, big};
  h.halo = el('circle', {r: big ? 8 : 6, fill: color, opacity: 0.18}, layer);
  h.dot = el('circle', {r: big ? 3.5 : 3, fill: color, stroke: D.ring, 'stroke-width': 2}, layer);
  heads.push(h);
  return h;
};

if (D.mode === 'lines') {
  svgs.forEach((svg, n) => {
    const paths = [...svg.querySelectorAll('path')];       // drawn in D.pathOrder in both the price and the drawdown panel
    paths.forEach(p => clip(svg, p));
    const layer = el('g', {}, svg); layers.push(layer);
    const pb = plotBox(svg);
    const cur = {pb, line: el('line', {y1: pb.y0, y2: pb.y1, stroke: D.axis, 'stroke-width': 1, 'stroke-dasharray': '2 3'}, layer), heads: []};
    cursors.push(cur);
    paths.forEach((p, i) => cur.heads.push(head(layer, p, D.pathOrder[i], p.getAttribute('stroke'), n === 0)));
    if (n === 0) {
      // the static line-end dots and labels come right after the last path; hidden until the draw is done
      for (let nd = paths[paths.length - 1].nextSibling; nd && nd !== layer; nd = nd.nextSibling)
        if (nd.nodeType === 1 && !nd.classList.contains('hov') && !(nd.id || '').startsWith('xh')) statics.push(nd);
      dateTag = el('text', {y: 10, 'text-anchor': 'middle', 'font-size': 10.5, 'font-weight': 600, fill: D.ink}, layer);
      labels = {hi: pb.y1, items: cur.heads.map(h => {
        const g = el('g', {}, layer), lead = el('line', {stroke: D.axis, 'stroke-width': 1}, g);
        const t = el('text', {'font-size': 12, fill: D.ink}, g);
        t.innerHTML = '<tspan font-weight="700"></tspan><tspan></tspan>';
        t.firstChild.textContent = D.series[h.sym].label;
        return {h, lead, t, val: t.lastChild};
      })};
    }
  });
} else {
  const svg = svgs[0], layer = el('g', {}, svg); layers.push(layer);
  const hdrs = [...svg.querySelectorAll('text')].filter(t => t.getAttribute('font-weight') === '700');
  hdrs.forEach((hdr, n) => {
    const sym = D.order[n], s = D.series[sym], nodes = [];
    for (let nd = hdr.nextSibling; nd && nd !== hdrs[n + 1] && nd !== layer; nd = nd.nextSibling) if (nd.nodeType === 1) nodes.push(nd);
    s.retEl = nodes.find(x => x.tagName === 'text' && x.getAttribute('font-weight') === '600');
    s.mddEl = nodes.find(x => x.tagName === 'text' && x !== s.retEl && /%$/.test(x.textContent));
    nodes.filter(x => ['path', 'polygon', 'polyline'].includes(x.tagName)).forEach(x => clip(svg, x));
    nodes.filter(x => x.tagName === 'circle').forEach(x => statics.push(x));
    const main = nodes.filter(x => x.tagName === 'path').pop();  // benchmark paths first, the stock's own line last
    head(layer, main, sym, main.getAttribute('stroke'), false);
  });
  const legend = box.querySelector('.legend');
  legend.style.position = 'relative';
  dateTag = document.createElement('span');
  dateTag.style.cssText = `position:absolute;right:12px;top:8px;font-weight:600;color:${D.ink};font-feature-settings:"tnum" 1;white-space:nowrap`;
  legend.appendChild(dateTag);
}

const rows = [...box.querySelectorAll('tbody tr')].map((tr, i) => {
  const td = [...tr.querySelectorAll('td')];
  return {sym: D.rowOrder[i], td, orig: td.map(t => t.innerHTML)};
});
const kOf = sym => { const h = heads.find(h => h.sym === sym); return Math.min(h.p.k, D.series[sym].idx.length - 1); };

window.__frame = (f, settle) => {
  const done = f >= 1 && settle >= 1;
  reveal.forEach(r => r.rect.setAttribute('width', f <= 0 ? 0 : 6 + f * (r.v[r.v.length - 1][0] - r.v[0][0]) + (f >= 1 ? 12 : 0)));
  statics.forEach(n => n.style.opacity = f >= 1 ? settle : 0);
  layers.forEach(l => l.style.opacity = f >= 1 ? 1 - settle : 1);
  heads.forEach(h => {
    h.p = at(h.v, f);
    for (const c of [h.halo, h.dot]) { c.setAttribute('cx', h.p.x); c.setAttribute('cy', h.p.y); }
  });
  const k0 = kOf(D.order[0]), dates = D.series[D.order[0]].dates;
  const when = fmtDate(dates[Math.min(Math.round(k0), dates.length - 1)]);
  if (D.mode === 'lines') {
    cursors.forEach(c => { const x = c.heads[0].p.x; c.line.setAttribute('x1', x); c.line.setAttribute('x2', x); c.line.style.opacity = f >= 1 ? 0 : 1; });
    const x = cursors[0].heads[0].p.x;
    dateTag.textContent = when;
    dateTag.setAttribute('x', Math.min(Math.max(x, cursors[0].pb.x0 + 34), cursors[0].pb.x1 - 34));
    dateTag.style.opacity = f >= 1 ? 0 : 1;
    // same collision rule as render_chart.spread(): sort by y, push down to `gap`, shift the stack up if it overflows
    const it = [...labels.items].sort((a, b) => a.h.p.y - b.h.p.y);
    it.forEach((o, i) => { o.ty = i ? Math.max(o.h.p.y, it[i - 1].ty + 16) : o.h.p.y; });
    const over = it.length ? it[it.length - 1].ty - labels.hi : 0;
    if (over > 0) it.forEach(o => o.ty -= over);
    it.forEach(o => {
      const s = D.series[o.h.sym], p = o.h.p;
      o.t.setAttribute('x', p.x + 14); o.t.setAttribute('y', o.ty + 4);
      o.val.textContent = '  ' + f1(lerp(s.idx, Math.min(p.k, s.idx.length - 1)) - 100, true) + '%';
      const off = Math.abs(o.ty - p.y) > 4;
      o.lead.style.display = off ? '' : 'none';
      if (off) { o.lead.setAttribute('x1', p.x + 4); o.lead.setAttribute('y1', p.y); o.lead.setAttribute('x2', p.x + 11); o.lead.setAttribute('y2', o.ty); }
    });
  } else {
    dateTag.textContent = when;
    dateTag.style.opacity = f >= 1 ? 1 - settle : 1;
    heads.forEach(h => {
      const s = D.series[h.sym], k = Math.min(h.p.k, s.idx.length - 1);
      s.retEl.textContent = done ? s.retOrig || s.retEl.textContent : f1(lerp(s.idx, k) - 100, true) + '%';
      if (s.mddEl) s.mddEl.textContent = s.mddEl.textContent.replace(/-?[\d.]+%$/, f1(done ? s.mddRun[s.mddRun.length - 1] : s.mddRun[Math.floor(k)]) + '%');
    });
  }
  rows.forEach(r => {
    if (done) { r.td.forEach((td, j) => { td.innerHTML = r.orig[j]; }); return; }
    const s = D.series[r.sym], k = kOf(r.sym), i = Math.floor(k);
    r.td[1].innerHTML = sg(lerp(s.idx, k) - 100);
    r.td[2].innerHTML = s.volRun[i].toFixed(1);
    r.td[3].innerHTML = sg(s.mddRun[i]);
    if (!s.na) r.td[4].innerHTML = s.prefix + money(lerp(s.close, k));
  });
};
// keep the static header texts of the small multiples to restore them exactly on the last frame
if (D.mode !== 'lines') Object.values(D.series).forEach(s => { if (s.retEl) s.retOrig = s.retEl.textContent; });
})();
"""

# Tables and holdings: window.__frame(f) with f = 0..1 (linear); row i runs from start[i] to start[i] + SPAN, each with its own easing.
# A row fades and rises in, its bars grow, and every number with a decimal point counts up from 0 in the row's own format;
# integers (ranks, share counts) and text just appear. Holdings' cumulative column is the running sum of the weights shown so far.
ROWS_JS = r"""
(() => {
const SPAN = __SPAN__;
const wrap = document.getElementById('wrap');
const NUM = /^([^\d(\-]*)(\(?)(-?)(\d[\d,]*\.(\d+))(\)?)(%?)$/;
const clamp = t => Math.min(Math.max(t, 0), 1);
const out3 = t => 1 - Math.pow(1 - t, 3);
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const show = (v, c) => {
  const a = Math.abs(v).toLocaleString('en-US', {minimumFractionDigits: c.dp, maximumFractionDigits: c.dp, useGrouping: c.comma});
  const neg = v < 0 && /[1-9]/.test(a);   // no "-0.0" while counting
  const n = !neg ? a : c.paren ? '(' + a + ')' : (c.sgn ? '<span class="sgn">-</span>' : '-') + a;
  return esc(c.pre) + n + c.pct;
};
const trs = [...wrap.querySelectorAll('tbody tr')];
const rows = trs.map((tr, i) => ({
  start: trs.length > 1 ? i * (1 - SPAN) / (trs.length - 1) : 0,
  tds: [...tr.children].map(td => ({td, style: td.getAttribute('style')})),
  bars: [...tr.querySelectorAll('.bar i')].map(b => ({b, w: parseFloat(b.style.width) || 0, style: b.getAttribute('style')})),
  nums: [...tr.children].flatMap(td => {
    const m = td.textContent.trim().match(NUM);
    if (!m) return [];
    const v = parseFloat(m[4].replace(/,/g, ''));
    return [{td, html: td.innerHTML, v: m[2] || m[3] ? -v : v, pre: m[1], paren: !!m[2], dp: m[5].length, pct: m[7],
             comma: m[4].includes(','), sgn: !!td.querySelector('.sgn'), cum: td.classList.contains('cum')}];
  }),
}));
window.__frame = f => {
  let run = 0;
  rows.forEach(r => {
    if (f >= 1) {   // exactly the static markup
      r.tds.forEach(o => o.style === null ? o.td.removeAttribute('style') : o.td.setAttribute('style', o.style));
      r.bars.forEach(o => o.b.setAttribute('style', o.style));
      r.nums.forEach(c => { c.td.innerHTML = c.html; });
      return;
    }
    const p = clamp((f - r.start) / SPAN), e = out3(p), a = clamp(p * 2.5);
    r.tds.forEach(o => { o.td.style.opacity = a; o.td.style.transform = `translateY(${((1 - out3(a)) * 8).toFixed(2)}px)`; });
    r.bars.forEach(o => { o.b.style.width = (o.w * e).toFixed(3) + '%'; });
    let shown = 0;
    r.nums.forEach(c => {
      const v = c.cum ? run + shown : c.v * e;
      if (!c.cum) shown = v;
      c.td.innerHTML = show(v, c);
    });
    if (r.nums.some(c => c.cum)) run += shown;
  });
};
})();
"""


def detect_kind(spec):
    """chart, table or holdings, from the input's own keys."""
    if isinstance(spec, dict):
        if isinstance(spec.get("holdings"), list):
            return "holdings"
        if "rows" in spec and "langs" in spec:
            return "table"
        if "data" in spec:
            return "chart"
    return None


def layout_of(spec, series):
    mode = spec.get("layout", "auto")
    return ("lines" if len(series) <= rc.MAX_LINES else "multiples") if mode == "auto" else mode


def motion_data(spec, d, series, benches, base, end, start, lang, theme="light"):
    """What the frame script needs: per-symbol data, and the order in which render_chart.py emits paths and table rows."""
    c = rc.Ctx(spec, d, series, benches, base, end, start, lang, theme)
    mode = layout_of(spec, series)
    conv = traditional if lang == "zh" else (lambda t: t)
    ser = {}
    for s in c.allk:
        cur = d["series"][s.sym].get("currency")
        ser[s.sym] = {"idx": s.idx, "dd": s.dd, "close": s.close, "dates": [x.isoformat() for x in s.dates],
                      "label": conv(c.bench_short(s) if s.is_bench else s.sym),
                      "na": s.is_bench or c.total, "prefix": f"{escape(cur)} " if cur else ""}
    return {
        "mode": mode, "lang": lang, "months": rc.S["en"]["months"], "series": ser,
        "order": [s.sym for s in (series if mode == "lines" else sorted(series, key=lambda s: -s.ret))],
        "pathOrder": [s.sym for s in benches[::-1] + series[::-1]],          # layout_lines draws benchmarks first, both reversed
        "rowOrder": [s.sym for s in sorted(c.allk, key=lambda s: -s.ret)],    # summary table: return, descending
        "ink": c.T["ink"], "axis": c.T["axis"], "ring": c.T["ring"],
    }


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0.0), 1.0))


def timeline(fps, intro, draw, settle, hold, eased=True):
    """[(f, settle)] per frame: the empty axes, a draw (eased for charts; linear for tables, whose rows ease one by one),
    a cross-fade to the static chart, a hold."""
    n, m = max(round(draw * fps), 2), max(round(settle * fps), 1)
    return ([(0.0, 0.0)] * round(intro * fps) + [((ease if eased else float)(i / (n - 1)), 0.0) for i in range(n)]
            + [(1.0, (i + 1) / m) for i in range(m)] + [(1.0, 1.0)] * round(hold * fps))


async def capture(html, script, frames, outdir, scale):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        reexec_in_venv()
        sys.exit("error: playwright is not installed. Run: pip install playwright && playwright install chromium")
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(device_scale_factor=scale, viewport={"width": 800, "height": 700})
        await pg.set_content(html)
        await pg.evaluate("document.fonts.ready")
        await pg.add_script_tag(content=script)
        wrap = pg.locator("#wrap")  # captured exactly like render_common, so the last frame equals the static PNG
        last = None
        for i, fs in enumerate(frames):
            out = outdir / f"f{i:05d}.png"
            if fs == last:
                shutil.copyfile(outdir / f"f{i - 1:05d}.png", out)
                continue
            await pg.evaluate("([f, s]) => window.__frame(f, s)", list(fs))
            await wrap.screenshot(path=str(out))
            last = fs
        await b.close()


def ff(*args):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit("error: ffmpeg failed: " + r.stderr[-800:])


def make_gif(fdir, fps, out, width, scale):
    """Looping GIF at most `width` px wide; narrower pages (the Blackstone table) keep their own CSS width."""
    vf = (f"fps={min(fps, 25)},scale='min({width},trunc(iw/{scale}))':-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];"
          "[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle")
    ff("-framerate", str(fps), "-i", str(fdir / "f%05d.png"), "-vf", vf, "-loop", "0", str(out))


def make_video(fdir, fps, out, max_side=None, faststart=True):
    sc = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    if max_side:
        sc = f"scale='if(gt(ih,iw),-2,min({max_side},iw))':'if(gt(ih,iw),min({max_side},ih),-2)':flags=lanczos,{sc}"
    ff("-framerate", str(fps), "-i", str(fdir / "f%05d.png"), "-vf", sc + ",format=yuv420p", "-c:v", "libx264", "-preset", "slow",
       "-crf", "16", "-tune", "animation", *(["-movflags", "+faststart"] if faststart else []), str(out))


# ---- Live Photo pairing ------------------------------------------------------------
def live_exif(cid):
    """APP1 payload whose only content is an Apple MakerNote with tag 17 = the Live Photo content identifier.
    The MakerNote bytes match what macOS ImageIO writes; MakerNote must be type UNDEFINED (7) or ImageIO ignores it."""
    s = cid.encode("ascii") + b"\0"
    mn = b"Apple iOS\0\x00\x01MM" + struct.pack(">HHHII", 1, 0x0011, 2, len(s), 32) + struct.pack(">I", 0) + s  # offsets from MakerNote start
    tiff = b"MM\x00\x2a" + struct.pack(">I", 8)
    ifd0 = struct.pack(">HHHII", 1, 0x8769, 4, 1, 26) + struct.pack(">I", 0)              # -> Exif IFD at 26
    exif_ifd = struct.pack(">HHHII", 1, 0x927C, 7, len(mn), 44) + struct.pack(">I", 0)    # -> MakerNote at 44
    return b"Exif\0\0" + tiff + ifd0 + exif_ifd + mn


def insert_exif(jpeg, exif):
    """Put `exif` in an APP1 segment right after SOI, dropping a JFIF APP0 if present."""
    if jpeg[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    rest = jpeg[2:]
    if rest[:2] == b"\xff\xe0":
        rest = rest[2 + struct.unpack(">H", rest[2:4])[0]:]
    return b"\xff\xd8\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif + rest


def atom(kind, body):
    return struct.pack(">I", 8 + len(body)) + kind + body


def stamp_mov(path, cid):
    """Add a QuickTime moov/meta (mdta keys) with com.apple.quicktime.content.identifier. moov must be the last atom
    (written without +faststart) so mdat does not move and no chunk offsets need patching."""
    data = bytearray(Path(path).read_bytes())
    pos, moov = 0, None
    while pos + 8 <= len(data):
        size, kind = struct.unpack(">I4s", data[pos:pos + 8])
        size = struct.unpack(">Q", data[pos + 8:pos + 16])[0] if size == 1 else (size or len(data) - pos)
        if size < 8:
            raise ValueError("malformed atom")
        if kind == b"moov":
            moov = (pos, size)
        pos += size
    if not moov or moov[0] + moov[1] != len(data):
        raise ValueError("expected moov as the last atom")
    meta = atom(b"meta",
                atom(b"hdlr", b"\0" * 8 + b"mdta" + b"\0" * 13)
                + atom(b"keys", b"\0" * 4 + struct.pack(">I", 1) + struct.pack(">I", 8 + len(LIVE_KEY)) + b"mdta" + LIVE_KEY)
                + atom(b"ilst", atom(struct.pack(">I", 1), atom(b"data", struct.pack(">II", 1, 0) + cid.encode("ascii")))))
    data[moov[0]:moov[0] + 4] = struct.pack(">I", moov[1] + len(meta))
    Path(path).write_bytes(bytes(data) + meta)


def make_live(fdir, n_frames, fps, out_prefix):
    cid = str(uuid.uuid4()).upper()
    mov, jpg = Path(f"{out_prefix}_live.mov"), Path(f"{out_prefix}_live.jpg")
    make_video(fdir, fps, mov, max_side=1920, faststart=False)
    stamp_mov(mov, cid)
    ff("-i", str(fdir / f"f{n_frames - 1:05d}.png"), "-q:v", "1", "-pix_fmt", "yuvj444p", str(jpg))  # key photo = the finished chart
    jpg.write_bytes(insert_exif(jpg.read_bytes(), live_exif(cid)))
    return jpg, mov, cid


def scripts(kind, spec, a, lang, chart=None, names=None):
    """(html, frame script, eased draw?) for one language. Exits with a message on bad input."""
    if kind == "chart":
        d, series, benches, base, end, start, _ = chart
        html = rc.build_html(spec, d, series, benches, base, end, start, lang, a.theme)
        data = motion_data(spec, d, series, benches, base, end, start, lang, a.theme)
        return html, FRAME_JS.replace("__DATA__", json.dumps(data, ensure_ascii=False)), True
    try:
        if kind == "table":
            html = rt.build_html(spec, lang, a.theme, a.style)
        else:
            html = rh.build_html(spec, lang, a.theme, a.top, a.mode, a.merge_classes, names, a.by)
    except (ValueError, KeyError, RuntimeError) as e:
        sys.exit(f"error: {e}")
    return html, ROWS_JS.replace("__SPAN__", "0.4"), False


def main():
    ap = argparse.ArgumentParser(description="Render an animated Schwab-style chart or table (GIF / MP4 / Live Photo).")
    ap.add_argument("spec", help="a render_chart.py or render_table.py spec, or fetch_holdings.py output")
    ap.add_argument("prefix")
    ap.add_argument("--formats", default="gif,mp4,live", help="comma-separated: gif, mp4, live (default: all three)")
    ap.add_argument("--langs", help="comma-separated (default: en,zh; a table spec: the languages it has)")
    ap.add_argument("--theme", choices=sorted(THEMES), default="light", help="light (default) or dark")
    ap.add_argument("--draw", type=float, default=3.6, help="seconds the lines or rows take to draw (default 3.6; Live Photos use at most 2.4)")
    ap.add_argument("--hold", type=float, default=1.6, help="seconds the finished image stays before the GIF / MP4 ends (default 1.6)")
    ap.add_argument("--fps", type=int, default=30, help="frames per second (default 30; GIFs are capped at 25)")
    ap.add_argument("--scale", type=float, default=2, help="pixel density of the frames (default 2, 1520 px wide)")
    ap.add_argument("--gif-width", type=int, default=760, help="largest GIF width in px (default 760; file size grows quickly with width)")
    g = ap.add_argument_group("table input (as render_table.py)")
    g.add_argument("--style", choices=STYLES, help="report template (default: spec.style, or schwab)")
    g = ap.add_argument_group("holdings input (as render_holdings.py)")
    g.add_argument("--top", type=int, default=13, help="how many holdings to show (default 13)")
    g.add_argument("--mode", choices=("exposure", "lines"), default="exposure")
    g.add_argument("--by", choices=rh.GROUPS, default="holding")
    g.add_argument("--merge-classes", action="store_true")
    g.add_argument("--names", help='JSON {"NVDA": {"zh": "英伟达"}} for local-language names')
    a = ap.parse_args()
    fmts = [x.strip() for x in a.formats.split(",") if x.strip()]
    bad = [x for x in fmts if x not in FORMATS]
    if bad or not fmts:
        sys.exit(f"error: --formats takes a comma-separated list of {', '.join(FORMATS)}")
    if not shutil.which("ffmpeg"):
        sys.exit("error: ffmpeg is not installed (macOS: brew install ffmpeg · Windows: winget install ffmpeg · Debian/Ubuntu: sudo apt install ffmpeg)")
    sp = Path(a.spec)
    try:
        spec = json.loads(sp.read_text(encoding="utf-8"))
        names = json.loads(Path(a.names).read_text(encoding="utf-8")) if a.names else {}
    except (OSError, ValueError) as e:
        sys.exit(f"error: cannot read input: {e}")
    kind = detect_kind(spec)
    if not kind:
        sys.exit(f"error: {sp} is not a chart spec (\"data\"), a table spec (\"langs\" + \"rows\") or fetch_holdings.py output (\"holdings\")")
    chart = None
    wanted = [x.strip() for x in a.langs.split(",")] if a.langs else None
    if kind == "chart":
        chart = rc.load(spec, sp.parent)
        d, series, benches, base, end, start, warnings = chart
        for w in warnings:
            print("warning:", w, file=sys.stderr)
        if layout_of(spec, series) == "lines" and len(series) > rc.MAX_LINES:
            sys.exit(f"error: lines layout supports at most {rc.MAX_LINES} symbols; use layout=multiples")
        langs = wanted or ["en", "zh"]
    elif kind == "table":
        langs = rt.pick_langs(spec, wanted)
    else:
        if not 1 <= a.top <= rh.MAX_TOP:
            sys.exit(f"error: --top must be between 1 and {rh.MAX_TOP}")
        langs = wanted or ["en", "zh"]
        if [l for l in langs if l not in rh.S]:
            sys.exit(f"error: unsupported language(s) for holdings (available: {', '.join(rh.S)})")
    Path(a.prefix).parent.mkdir(parents=True, exist_ok=True)
    for lang in langs:
        html, script, eased = scripts(kind, spec, a, lang, chart, names)
        out = f"{a.prefix}_{lang}"
        with tempfile.TemporaryDirectory() as tmp:
            if "gif" in fmts or "mp4" in fmts:
                fdir = Path(tmp) / "loop"
                fdir.mkdir()
                asyncio.run(capture(html, script, timeline(a.fps, 0.4, a.draw, 0.5, a.hold, eased), fdir, a.scale))
                if "gif" in fmts:
                    make_gif(fdir, a.fps, f"{out}.gif", a.gif_width, a.scale)
                    print(f"wrote {out}.gif")
                if "mp4" in fmts:
                    make_video(fdir, a.fps, f"{out}.mp4")
                    print(f"wrote {out}.mp4")
            if "live" in fmts:
                fdir = Path(tmp) / "live"
                fdir.mkdir()
                frames = timeline(a.fps, 0.2, min(a.draw, 2.4), 0.3, 0.3, eased)  # about 3 s, ending on the key photo
                asyncio.run(capture(html, script, frames, fdir, a.scale))
                jpg, mov, cid = make_live(fdir, len(frames), a.fps, out)
                print(f"wrote {jpg} + {mov} (Live Photo, content identifier {cid})")
    if kind == "chart":
        print("base date:", base, "| end:", end, "| " + ", ".join(f"{s.sym} {rc.f1(s.ret, True)}%" for s in series + benches))


if __name__ == "__main__":
    main()
