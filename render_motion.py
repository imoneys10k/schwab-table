"""Animated charts and tables that settle on the exact static image.

Usage: python3 render_motion.py INPUT.json OUT_PREFIX [--formats gif,webp,mp4,live] [--langs en,zh] [--theme light|dark]
                                [--draw 3.6] [--hold 1.6] [--fps 30] [--scale 2] [--gif-width 760]
       table input:    [--style schwab|morgan|blackstone|ibkr]
       holdings input: [--top 13] [--mode exposure|lines] [--by holding|name|sector] [--merge-classes] [--names names.json]

INPUT is any of the three inputs the static renderers take, recognised by its content:
  price chart  render_chart.py spec ("data" key)            the lines draw left to right; labels, table and date follow the cursor
  table        render_table.py spec ("langs" + "rows")      rows come in one after another and their numbers count up
  holdings     fetch_holdings.py output ("holdings" list)   bars grow one after another, weights and the cumulative column count up
Per language it writes:
  gif   OUT_PREFIX_{lang}.gif                       looping GIF (chat apps, X, web pages)
  webp  OUT_PREFIX_{lang}.webp                      the same as an animated WebP: full colour, about a third smaller (web pages,
                                                    Telegram, Discord; not every chat app plays it). Needs Pillow; not in the default set
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
import re
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import uuid
from concurrent.futures import ThreadPoolExecutor
from html import escape
from pathlib import Path

import render_chart as rc
import render_holdings as rh
import render_table as rt
from institutional_tables import STYLES
from localization import traditional
from render_common import THEMES, reexec_in_venv

FORMATS = ("gif", "webp", "mp4", "live")
LOOP_FADE = {"gif": 0.0, "webp": 0.0, "mp4": 0.4}   # default --loop-fade per format
KINDS = ("chart", "table", "holdings")
LIVE_KEY = b"com.apple.quicktime.content.identifier"
STILL_KEY = b"com.apple.quicktime.still-image-time"
STILL_SAMPLE = struct.pack(">II", 9, 1) + b"\xff"   # one item: size 9, local key 1, int8 -1 (what iPhone and AVFoundation write)
LIVE_FPS = 30                                        # iPhone Live Photos are 30 fps; a higher --fps only changes the GIF / MP4
CANVASES = ("1:1", "4:5", "3:4", "9:16", "16:9")

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
  return {sym: D.rowOrder[i], td, orig: td.map(t => t.innerHTML), style: td.map(t => t.getAttribute('style'))};
});
const slot = rows.map(r => r.td[0].getBoundingClientRect().top);   // where each rank sits in the static table
// data index of a series at draw fraction f; a series without its own moving head (a benchmark in the small multiples) follows the
// first head's share of the period
const kAt = (sym, f) => {
  const h = heads.find(h => h.sym === sym), n = D.series[sym].idx.length - 1;
  if (h) return Math.min(at(h.v, f).k, n);
  const h0 = heads[0];
  return Math.min(at(h0.v, f).k / Math.max(D.series[h0.sym].idx.length - 1, 1) * n, n);
};
const kOf = sym => kAt(sym, heads[0].f);
// The summary table stays sorted by the return so far. Replayed over the whole draw once, on returns averaged over the last
// SMOOTH of the draw: a row passes the one above it only when it leads by PASS of the current spread (at least 2 points), so
// lines running close together do not make the rows flicker; at the end the order is the static one. Each pass becomes an eased
// slide of SLIDE of the draw's running time (f is eased, so time is recovered from it) that starts when it happens.
const SMOOTH = 0.05, PASS = 0.06, SLIDE = 0.05;
const clock = f => Math.acos(1 - 2 * Math.min(Math.max(f, 0), 1)) / Math.PI;   // inverse of the draw's cosine easing
const slides = (() => {
  let order = rows.map((_, i) => i);
  const out = [], at = o => { const r = []; o.forEach((i, pos) => { r[i] = pos; }); return r; };
  const ret = (r, t) => [0, 1, 2, 3, 4].reduce((a, j) => a + lerp(D.series[r.sym].idx, kAt(r.sym, Math.max(t - SMOOTH * j / 4, 0))), 0) / 5;
  for (let s = 1; s <= 300; s++) {
    const t = s / 300, v = rows.map(r => ret(r, t)), gap = Math.max(2, PASS * (Math.max(...v) - Math.min(...v)));
    const before = at(order);
    if (t === 1) order = rows.map((_, i) => i);
    else for (let pass = 0; pass < order.length; pass++)
      for (let q = 0; q + 1 < order.length; q++)
        if (v[order[q + 1]] - v[order[q]] > gap) order.splice(q, 2, order[q + 1], order[q]);
    const after = at(order);
    if (after.some((x, i) => x !== before[i])) out.push({c: clock(t), d: after.map((x, i) => x - before[i])});
  }
  return out;
})();
const rankAt = (i, f) => slides.reduce((r, e) => r + e.d[i] * (0.5 - 0.5 * Math.cos(Math.PI * Math.min(Math.max((clock(f) - e.c) / SLIDE, 0), 1))), i);

window.__frame = (f, settle) => {
  const done = f >= 1 && settle >= 1;
  reveal.forEach(r => r.rect.setAttribute('width', f <= 0 ? 0 : 6 + f * (r.v[r.v.length - 1][0] - r.v[0][0]) + (f >= 1 ? 12 : 0)));
  statics.forEach(n => n.style.opacity = f >= 1 ? settle : 0);
  layers.forEach(l => l.style.opacity = f >= 1 ? 1 - settle : 1);
  heads.forEach(h => {
    h.f = f;
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
    if (done) {
      r.td.forEach((td, j) => { td.innerHTML = r.orig[j]; r.style[j] === null ? td.removeAttribute('style') : td.setAttribute('style', r.style[j]); });
      return;
    }
    const s = D.series[r.sym], k = kOf(r.sym), i = Math.floor(k);
    r.td[1].innerHTML = sg(lerp(s.idx, k) - 100);
    r.td[2].innerHTML = s.volRun[i].toFixed(1);
    r.td[3].innerHTML = sg(s.mddRun[i]);
    if (!s.na) r.td[4].innerHTML = s.prefix + money(lerp(s.close, k));
  });
  if (done) return;
  rows.forEach((r, i) => {
    let rank = rankAt(i, f);
    if (f >= 1) rank += (i - rank) * settle;
    const lo = Math.min(Math.floor(rank), slot.length - 1), y = slot[lo] + (rank - lo) * ((slot[lo + 1] ?? slot[lo]) - slot[lo]);
    r.td.forEach(td => { td.style.transform = `translateY(${(y - slot[i]).toFixed(2)}px)`; td.style.background = D.bg; });
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
        "ink": c.T["ink"], "axis": c.T["axis"], "ring": c.T["ring"], "bg": c.T["bg"],
    }


def ease(t):
    return 0.5 - 0.5 * math.cos(math.pi * min(max(t, 0.0), 1.0))


def segments(fps, intro, draw, settle, hold, eased=True):
    """The four parts of a timeline as lists of (f, settle) states: the empty start, a draw (eased for charts; linear for tables,
    whose rows ease one by one), a cross-fade to the static image, a hold."""
    n, m = max(round(draw * fps), 2), max(round(settle * fps), 1)
    return ([(0.0, 0.0)] * round(intro * fps), [((ease if eased else float)(i / (n - 1)), 0.0) for i in range(n)],
            [(1.0, (i + 1) / m) for i in range(m)], [(1.0, 1.0)] * round(hold * fps))


def timeline(fps, intro, draw, settle, hold, eased=True):
    """[(f, settle)] per frame."""
    return [x for part in segments(fps, intro, draw, settle, hold, eased) for x in part]


def thin(states, n):
    """n states picked evenly from `states` (all of them if there are fewer), first and last included."""
    if n >= len(states):
        return list(states)
    return [states[round(i * (len(states) - 1) / max(n - 1, 1))] for i in range(n)]


def live_timeline(loop, draw):
    """About 3 s at LIVE_FPS, made only of states the loop already has, so no frame is captured twice: the draw is thinned to at
    most 2.4 s and the cross-fade to 0.3 s, and the last frame (the key photo) is the finished image."""
    _, d, st, _ = loop
    return ([(0.0, 0.0)] * round(0.2 * LIVE_FPS) + thin(d, round(min(draw, 2.4) * LIVE_FPS)) + thin(st, round(0.3 * LIVE_FPS))
            + [(1.0, 1.0)] * round(0.3 * LIVE_FPS))


def table_draw(rows):
    """Seconds for a table's rows to come in, by row count: 6 rows take about 2.2 s, 16 rows 4.4 s, 30 rows or more 6 s."""
    return min(max(0.9 + 0.22 * rows, 2.0), 6.0)


def row_span(draw):
    """Share of the draw one row takes to come in: about 0.7 s, between 12 % and 60 %."""
    return min(max(0.7 / draw, 0.12), 0.6)


async def capture_all(jobs, scale):
    """jobs = [(html, script, states, outdir)]. One browser with a page per job, all running at once; each distinct state is
    captured once. Returns {state: png path} per job."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        reexec_in_venv()
        sys.exit("error: playwright is not installed. Run: pip install playwright && playwright install chromium")

    async def run(b, html, script, states, outdir):
        pg = await b.new_page(device_scale_factor=scale, viewport={"width": 800, "height": 700})
        await pg.set_content(html)
        await pg.evaluate("document.fonts.ready")
        await pg.add_script_tag(content=script)
        wrap = pg.locator("#wrap")  # captured exactly like render_common, so the finished frame equals the static PNG
        shots = {}
        for st in dict.fromkeys(states):
            await pg.evaluate("([f, s]) => window.__frame(f, s)", list(st))
            shots[st] = outdir / f"s{len(shots):05d}.png"
            await wrap.screenshot(path=str(shots[st]))
        await pg.close()
        return shots

    async with async_playwright() as p:
        b = await p.chromium.launch()
        try:
            return await asyncio.gather(*(run(b, *job) for job in jobs))
        finally:
            await b.close()


def sequence(shots, states, d):
    """d/f00000.png ... in timeline order, as hard links to the captured states (copies where links are not possible)."""
    d.mkdir()
    for i, st in enumerate(states):
        try:
            os.link(shots[st], d / f"f{i:05d}.png")
        except OSError:
            shutil.copyfile(shots[st], d / f"f{i:05d}.png")
    return d


def ff(*args):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], capture_output=True, text=True)
    if r.returncode:
        sys.exit("error: ffmpeg failed: " + r.stderr[-800:])


def png_size(path):
    with open(path, "rb") as f:
        return struct.unpack(">II", f.read(24)[16:24])


def pad(size, canvas, bg):
    """ffmpeg filter (with a trailing comma) that centres the frame on a canvas of aspect ratio `canvas` ("3:4"), filled with the
    page colour; empty when no canvas is asked for."""
    if not canvas:
        return ""
    (w, h), (a, b) = size, map(int, canvas.split(":"))
    cw, ch = (w, math.ceil(w * b / a)) if w * b >= h * a else (math.ceil(h * a / b), h)
    c = bg.lstrip("#")
    c = "".join(x * 2 for x in c) if len(c) == 3 else c
    return f"pad={cw + cw % 2}:{ch + ch % 2}:(ow-iw)/2:(oh-ih)/2:color=0x{c},"


def loop_input(fdir, n, fps, fade):
    """ffmpeg inputs and the start of the filter graph for a looping clip. With a fade, the end cross-fades into the first frame, so
    the loop restarts without a jump."""
    args = ["-framerate", str(fps), "-i", str(fdir / "f%05d.png")]
    head = f"[0:v]trim=end_frame={n}"   # formats with a shorter fade leave the tail of the shared frames unused
    if fade <= 0:
        return args, head + ","
    args += ["-framerate", str(fps), "-loop", "1", "-t", f"{fade + 2 / fps:.4f}", "-i", str(fdir / "f00000.png")]
    return args, f"{head}[m];[m][1:v]xfade=transition=fade:duration={fade:.4f}:offset={n / fps - fade:.4f},"


def small(fdir, n, fps, width, scale, fade, canvas):
    """ffmpeg inputs and filter graph for a GIF or WebP: at most `width` px wide (narrower pages, such as the Blackstone table, keep
    their own CSS width), 25 fps at most: GIF frame delays are whole hundredths of a second, so 30 fps cannot be shown evenly."""
    args, head = loop_input(fdir, n, fps, fade)
    return args, f"{head}{canvas}fps={min(fps, 25)},scale='min({width},trunc(iw/{scale}))':-1:flags=lanczos"


def make_gif(fdir, n, fps, out, width, scale, fade=0.0, canvas=""):
    args, graph = small(fdir, n, fps, width, scale, fade, canvas)
    graph += ",split[a][b];[a]palettegen=max_colors=256:stats_mode=full[p];[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle"
    ff(*args, "-filter_complex", graph, "-loop", "0", str(out))


def make_webp(fdir, n, fps, out, width, scale, fade=0.0, canvas=""):
    """Animated WebP, sized and timed like the GIF but in full colour and about a third smaller. ffmpeg builds often lack the WebP
    encoder, so ffmpeg writes an APNG that Pillow re-encodes one frame at a time. Quality 80 keeps text as sharp as the GIF's; with
    key frames off, each frame stores only what changed, and unchanged frames merge."""
    from PIL import Image
    args, graph = small(fdir, n, fps, width, scale, fade, canvas)
    mid = fdir.parent / f"{Path(out).stem}.apng"
    ff(*args, "-filter_complex", graph, "-compression_level", "1", "-f", "apng", str(mid))
    with Image.open(mid) as im:
        im.save(out, "WEBP", save_all=True, duration=round(1000 / min(fps, 25)), loop=0, quality=80, method=4,
                allow_mixed=True, kmin=0, kmax=0)


def make_video(fdir, n, fps, out, max_side=None, faststart=True, fade=0.0, canvas=""):
    args, head = loop_input(fdir, n, fps, fade)
    sc = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    if max_side:
        sc = f"scale='if(gt(ih,iw),-2,min({max_side},iw))':'if(gt(ih,iw),min({max_side},ih),-2)':flags=lanczos,{sc}"
    ff(*args, "-filter_complex", f"{head}{canvas}{sc},format=yuv420p", "-c:v", "libx264", "-preset", "slow",
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


def pascal(text):
    return bytes([len(text)]) + text.encode("ascii")


def still_track(track_id, timescale, duration, still, offset):
    """A timed-metadata track holding one sample, com.apple.quicktime.still-image-time = -1, at `still` (movie time units): it
    marks which moment of the video the key photo shows. The atoms are laid out as AVFoundation's AVAssetWriter writes them."""
    frame = max(1, round(timescale / LIVE_FPS))
    still = max(0, min(still, duration - frame))
    ident = (0x10000, 0, 0, 0, 0x10000, 0, 0, 0, 0x40000000)
    tkhd = b"\x00\x00\x00\x0f" + struct.pack(">IIIII", 0, 0, track_id, 0, duration) + b"\0" * 8 + struct.pack(">hhhH", 0, 0, 0, 0) \
        + struct.pack(">9I", *ident) + struct.pack(">II", 0, 0)
    edits = ([(still, -1)] if still else []) + [(frame, 0)]                       # an empty edit places the sample at `still`
    elst = b"\0" * 4 + struct.pack(">I", len(edits)) + b"".join(struct.pack(">IiI", d, t, 0x10000) for d, t in edits)
    mdhd = b"\0" * 4 + struct.pack(">IIIIHH", 0, 0, timescale, frame, 0x55C4, 0)
    keys = atom(struct.pack(">I", 1), atom(b"keyd", b"mdta" + STILL_KEY) + atom(b"dtyp", struct.pack(">II", 0, 65)))  # 65 = signed int8
    stbl = (atom(b"stsd", b"\0" * 4 + struct.pack(">I", 1) + atom(b"mebx", b"\0" * 6 + struct.pack(">H", 1) + atom(b"keys", keys)))
            + atom(b"stts", b"\0" * 4 + struct.pack(">III", 1, 1, frame)) + atom(b"stsc", b"\0" * 4 + struct.pack(">IIII", 1, 1, 1, 1))
            + atom(b"stsz", b"\0" * 4 + struct.pack(">II", len(STILL_SAMPLE), 1)) + atom(b"stco", b"\0" * 4 + struct.pack(">II", 1, offset)))
    minf = (atom(b"gmhd", atom(b"gmin", b"\0" * 4 + struct.pack(">HHHHhH", 0x40, 0x8000, 0x8000, 0x8000, 0, 0)))
            + atom(b"hdlr", b"\0" * 4 + b"dhlr" + b"alis" + b"appl" + struct.pack(">II", 0, 0) + pascal("Core Media Data Handler"))
            + atom(b"dinf", atom(b"dref", b"\0" * 4 + struct.pack(">I", 1) + atom(b"alis", b"\0\0\0\x01"))) + atom(b"stbl", stbl))
    mdia = (atom(b"mdhd", mdhd) + atom(b"hdlr", b"\0" * 4 + b"mhlr" + b"meta" + b"appl" + struct.pack(">II", 1, 0) + pascal("Core Media Metadata"))
            + atom(b"minf", minf))
    return atom(b"trak", atom(b"tkhd", tkhd) + atom(b"edts", atom(b"elst", elst)) + atom(b"mdia", mdia))


def stamp_mov(path, cid, still=None):
    """Add a QuickTime moov/meta (mdta keys) with com.apple.quicktime.content.identifier and, if `still` (seconds) is given, the
    still-image-time track. moov must be the last atom (written without +faststart) so the video's mdat does not move and no chunk
    offsets need patching; the still sample goes in a small mdat after moov."""
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
    extra, tail = meta, b""
    if still is not None:
        mvhd = data.find(b"mvhd", moov[0], moov[0] + moov[1]) - 4
        size, v = struct.unpack(">I", data[mvhd:mvhd + 4])[0], data[mvhd + 8]
        timescale, duration = struct.unpack(">II", data[mvhd + 20:mvhd + 28]) if v == 0 else struct.unpack(">IQ", data[mvhd + 28:mvhd + 40])
        track_id = struct.unpack(">I", data[mvhd + size - 4:mvhd + size])[0]
        data[mvhd + size - 4:mvhd + size] = struct.pack(">I", track_id + 1)        # mvhd next_track_ID
        at = round(still * timescale)
        trak = still_track(track_id, timescale, duration, at, 0)
        offset = moov[0] + moov[1] + len(meta) + len(trak) + 8                      # the sample, inside the mdat after moov
        extra, tail = meta + still_track(track_id, timescale, duration, at, offset), atom(b"mdat", STILL_SAMPLE)
    data[moov[0]:moov[0] + 4] = struct.pack(">I", moov[1] + len(extra))
    Path(path).write_bytes(bytes(data) + extra + tail)


def make_live(fdir, n_frames, out_prefix, canvas=""):
    """The Live Photo pair from frames f00000..: a MOV at LIVE_FPS and a JPEG key photo (the last frame), sharing a content
    identifier; the MOV marks the last frame as the still-image time."""
    cid = str(uuid.uuid4()).upper()
    mov, jpg = Path(f"{out_prefix}_live.mov"), Path(f"{out_prefix}_live.jpg")
    make_video(fdir, n_frames, LIVE_FPS, mov, max_side=1920, faststart=False, canvas=canvas)
    stamp_mov(mov, cid, still=(n_frames - 1) / LIVE_FPS)
    ff("-i", str(fdir / f"f{n_frames - 1:05d}.png"), "-vf", canvas.rstrip(",") or "null", "-q:v", "1", "-pix_fmt", "yuvj444p", str(jpg))
    jpg.write_bytes(insert_exif(jpg.read_bytes(), live_exif(cid)))
    return jpg, mov, cid


def scripts(kind, spec, a, lang, chart=None, names=None):
    """(html, frame script, eased draw?, draw seconds) for one language. Tables and holdings get a draw time from their row count
    unless --draw is given. Exits with a message on bad input."""
    if kind == "chart":
        d, series, benches, base, end, start, _ = chart
        html = rc.build_html(spec, d, series, benches, base, end, start, lang, a.theme)
        data = motion_data(spec, d, series, benches, base, end, start, lang, a.theme)
        return html, FRAME_JS.replace("__DATA__", json.dumps(data, ensure_ascii=False)), True, a.draw or 3.6
    try:
        if kind == "table":
            html = rt.build_html(spec, lang, a.theme, a.style)
        else:
            html = rh.build_html(spec, lang, a.theme, a.top, a.mode, a.merge_classes, names, a.by)
    except (ValueError, KeyError, RuntimeError) as e:
        sys.exit(f"error: {e}")
    draw = a.draw or table_draw(sum(t.count("<tr") for t in re.findall(r"<tbody>(.*?)</tbody>", html, re.S)))
    return html, ROWS_JS.replace("__SPAN__", f"{row_span(draw):.4f}"), False, draw


def main():
    ap = argparse.ArgumentParser(description="Render an animated Schwab-style chart or table (GIF / MP4 / Live Photo).")
    ap.add_argument("spec", help="a render_chart.py or render_table.py spec, or fetch_holdings.py output")
    ap.add_argument("prefix")
    ap.add_argument("--formats", default="gif,mp4,live", help="comma-separated: gif, webp, mp4, live (default: gif,mp4,live; "
                    "webp needs Pillow)")
    ap.add_argument("--langs", help="comma-separated (default: en,zh; a table spec: the languages it has)")
    ap.add_argument("--theme", choices=sorted(THEMES), default="light", help="light (default) or dark")
    ap.add_argument("--canvas", choices=CANVASES, help="centre the image on a canvas of this aspect ratio, filled with the page colour "
                    "(3:4 or 4:5 for Xiaohongshu and Instagram, 9:16 for Reels, TikTok and Douyin; default: the image's own size)")
    ap.add_argument("--draw", type=float, help="seconds the lines or rows take to draw (default: 3.6 for charts; for tables and holdings "
                    "2 to 6 by row count; Live Photos use at most 2.4)")
    ap.add_argument("--hold", type=float, default=1.6, help="seconds the finished image stays before the GIF / MP4 loops (default 1.6)")
    ap.add_argument("--loop-fade", type=float, help="seconds the end cross-fades into the first frame, so the loop has no jump "
                    "(default: 0.4 for the MP4, none for the GIF and WebP, where the fade frames cost about a fifth more file size; 0 for a hard cut)")
    ap.add_argument("--fps", type=int, default=30, help="frames per second of the MP4 (default 30; 60 is smoother and takes about twice "
                    "as long; GIF and WebP are capped at 25, Live Photos are 30)")
    ap.add_argument("--scale", type=float, default=2, help="pixel density of the frames (default 2, 1520 px wide)")
    ap.add_argument("--gif-width", type=int, default=760, help="largest GIF / WebP width in px (default 760; file size grows quickly with width)")
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
    if a.draw is not None and a.draw <= 0 or a.hold < 0 or (a.loop_fade or 0) < 0 or a.fps < 1:
        sys.exit("error: --draw and --fps must be positive, --hold and --loop-fade zero or more")
    if "webp" in fmts:
        try:
            from PIL import features
            ok = features.check("webp")
        except ImportError:
            ok = False
        if not ok:
            sys.exit("error: WebP output needs Pillow with WebP support: python3 -m pip install pillow")
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
    looped = [f for f in fmts if f in LOOP_FADE]
    fade = {f: a.loop_fade if a.loop_fade is not None else LOOP_FADE[f] for f in looped}
    tail = max(fade.values(), default=0)   # the shared frames hold long enough for the longest fade
    with tempfile.TemporaryDirectory() as tmp:
        jobs, plans = [], []
        for lang in langs:   # every language is captured at once, each distinct frame once for all three formats
            html, script, eased, draw = scripts(kind, spec, a, lang, chart, names)
            loop = segments(a.fps, 0.4, draw, 0.5, a.hold + tail, eased)
            seq = {"loop": [x for part in loop for x in part] if looped else [], "live": live_timeline(loop, draw) if "live" in fmts else []}
            work = Path(tmp) / lang
            work.mkdir()
            jobs.append((html, script, seq["loop"] + seq["live"], work))
            plans.append((lang, seq, work))
        shots = asyncio.run(capture_all(jobs, a.scale))
        tasks = []
        for (lang, seq, work), shot in zip(plans, shots):
            out = f"{a.prefix}_{lang}"
            canvas = pad(png_size(next(iter(shot.values()))), a.canvas, THEMES[a.theme]["bg"])
            if looped:
                fdir = sequence(shot, seq["loop"], work / "loop")
                n = {f: len(seq["loop"]) - round((tail - x) * a.fps) for f, x in fade.items()}
                for f, make in (("gif", make_gif), ("webp", make_webp)):
                    if f in fmts:
                        tasks.append((make, (fdir, n[f], a.fps, f"{out}.{f}", a.gif_width, a.scale, fade[f], canvas), {}, f"wrote {out}.{f}"))
                if "mp4" in fmts:
                    tasks.append((make_video, (fdir, n["mp4"], a.fps, f"{out}.mp4"), dict(fade=fade["mp4"], canvas=canvas), f"wrote {out}.mp4"))
            if "live" in fmts:
                fdir = sequence(shot, seq["live"], work / "live")
                tasks.append((make_live, (fdir, len(seq["live"]), out, canvas), {}, f"wrote {out}_live.jpg + {out}_live.mov (Live Photo)"))
        with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as pool:   # ffmpeg encodes run side by side too
            for fut, msg in [(pool.submit(fn, *args, **kw), msg) for fn, args, kw, msg in tasks]:
                fut.result()
                print(msg)
    if kind == "chart":
        print("base date:", base, "| end:", end, "| " + ", ".join(f"{s.sym} {rc.f1(s.ret, True)}%" for s in series + benches))


if __name__ == "__main__":
    main()
