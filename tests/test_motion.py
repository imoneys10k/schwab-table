"""Animated charts: Live Photo metadata, frame timeline and the element order the frame script relies on. No browser or ffmpeg needed."""
import json
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import render_chart as rc  # noqa: E402
import render_holdings as rh  # noqa: E402
import render_motion as rm  # noqa: E402
import render_table as rt  # noqa: E402

CID = "3ED4251C-446C-40D2-8FD1-4700273D9310"


def atoms(buf, start=0, end=None):
    """[(kind, body_start, body_end)] of the atoms between start and end."""
    out, pos, end = [], start, len(buf) if end is None else end
    while pos + 8 <= end:
        size, kind = struct.unpack(">I4s", buf[pos:pos + 8])
        out.append((kind, pos + 8, pos + size))
        pos += size
    return out


class LivePhotoImage(unittest.TestCase):
    def test_makernote_holds_the_content_identifier(self):
        exif = rm.live_exif(CID)
        self.assertTrue(exif.startswith(b"Exif\0\0"))
        t = exif[6:]
        self.assertEqual(t[:4], b"MM\x00\x2a")
        ifd0 = struct.unpack(">I", t[4:8])[0]
        tag, typ, cnt, exif_ifd = struct.unpack(">HHII", t[ifd0 + 2:ifd0 + 14])
        self.assertEqual((tag, typ, cnt), (0x8769, 4, 1))
        tag, typ, cnt, off = struct.unpack(">HHII", t[exif_ifd + 2:exif_ifd + 14])
        self.assertEqual((tag, typ), (0x927C, 7))   # MakerNote must be UNDEFINED; ImageIO ignores a BYTE MakerNote
        mn = t[off:off + cnt]
        self.assertEqual(mn[:14], b"Apple iOS\0\x00\x01MM")
        n = struct.unpack(">H", mn[14:16])[0]
        tag, typ, cnt, voff = struct.unpack(">HHII", mn[16:28])
        self.assertEqual((n, tag, typ), (1, 0x0011, 2))  # tag 17, ASCII, offsets relative to the MakerNote start
        self.assertEqual(mn[voff:voff + cnt], CID.encode() + b"\0")

    def test_exif_goes_right_after_soi_and_replaces_jfif(self):
        app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\0" + b"\x01\x01\0\0\x01\0\x01\0\0"
        body = b"\xff\xdb\x00\x03\x00\xff\xd9"
        out = rm.insert_exif(b"\xff\xd8" + app0 + body, rm.live_exif(CID))
        self.assertEqual(out[:4], b"\xff\xd8\xff\xe1")
        n = struct.unpack(">H", out[4:6])[0]
        self.assertEqual(out[6:6 + n - 2], rm.live_exif(CID))
        self.assertEqual(out[4 + n:], body)
        self.assertNotIn(b"JFIF", out)
        with self.assertRaises(ValueError):
            rm.insert_exif(b"\x89PNG", b"")


class LivePhotoVideo(unittest.TestCase):
    def write(self, *parts):
        f = tempfile.NamedTemporaryFile(suffix=".mov", delete=False)
        f.write(b"".join(parts))
        f.close()
        self.addCleanup(Path(f.name).unlink)
        return f.name

    def test_meta_keys_and_value_are_added_to_moov(self):
        mdat = rm.atom(b"mdat", b"\x01\x02\x03\x04" * 8)
        moov = rm.atom(b"moov", rm.atom(b"mvhd", b"\0" * 100))
        p = self.write(rm.atom(b"ftyp", b"qt  \0\0\0\0qt  "), mdat, moov)
        before = Path(p).read_bytes()
        rm.stamp_mov(p, CID)
        buf = Path(p).read_bytes()
        head = len(before) - len(moov)
        self.assertEqual(buf[:head], before[:head])                                # ftyp and mdat did not move
        self.assertEqual(buf[head + 8:len(before)], moov[8:])                      # the old moov children are untouched
        top = atoms(buf)
        self.assertEqual([k for k, _, _ in top], [b"ftyp", b"mdat", b"moov"])
        self.assertEqual(top[-1][2], len(buf))                                     # moov size covers the new meta
        inner = {k: (a, b) for k, a, b in atoms(buf, top[-1][1], top[-1][2])}
        meta = {k: (a, b) for k, a, b in atoms(buf, *inner[b"meta"])}
        self.assertEqual(buf[meta[b"hdlr"][0] + 8:meta[b"hdlr"][0] + 12], b"mdta")
        keys = buf[meta[b"keys"][0]:meta[b"keys"][1]]
        self.assertEqual(struct.unpack(">I", keys[4:8])[0], 1)
        self.assertEqual(keys[12:16] + keys[16:], b"mdta" + rm.LIVE_KEY)
        (idx, a, b), = atoms(buf, *meta[b"ilst"])
        self.assertEqual(struct.unpack(">I", idx)[0], 1)
        (kind, da, db), = atoms(buf, a, b)
        self.assertEqual(kind, b"data")
        self.assertEqual(struct.unpack(">II", buf[da:da + 8]), (1, 0))             # UTF-8, default locale
        self.assertEqual(buf[da + 8:db], CID.encode())

    def test_refuses_a_file_whose_moov_is_not_last(self):
        p = self.write(rm.atom(b"ftyp", b"qt  "), rm.atom(b"moov", b""), rm.atom(b"mdat", b"x"))
        with self.assertRaises(ValueError):
            rm.stamp_mov(p, CID)


class Timeline(unittest.TestCase):
    def test_shape(self):
        fr = rm.timeline(30, 0.4, 3.6, 0.5, 1.6)
        self.assertEqual(len(fr), 12 + 108 + 15 + 48)
        self.assertEqual(fr[0], (0.0, 0.0))
        self.assertEqual(fr[-1], (1.0, 1.0))
        draw = [f for f, s in fr if s == 0]
        self.assertEqual(draw, sorted(draw))
        self.assertAlmostEqual(max(draw), 1.0)
        settle = [s for f, s in fr if f == 1.0]
        self.assertEqual(settle, sorted(settle))

    def test_tables_draw_linearly(self):
        draw = [f for f, s in rm.timeline(10, 0, 1.0, 0.1, 0, eased=False) if s == 0]
        self.assertEqual(draw, [i / 9 for i in range(10)])   # each row eases on its own; the overall clock is linear


class InputKind(unittest.TestCase):
    def kind(self, name):
        return rm.detect_kind(json.loads((ROOT / "examples" / name).read_text(encoding="utf-8")))

    def test_every_example_input_is_recognised(self):
        self.assertEqual(self.kind("chart_lines_spec.json"), "chart")
        self.assertEqual(self.kind("chart_multiples_spec.json"), "chart")
        for t in ("watchlist", "neural9", "holdings", "morgan", "ibkr", "blackstone"):
            self.assertEqual(self.kind(f"{t}_spec.json"), "table", t)
        self.assertEqual(self.kind("etf_holdings_swap.json"), "holdings")
        self.assertEqual(self.kind("etf_holdings_equity.json"), "holdings")
        self.assertIsNone(rm.detect_kind({"rows": []}))
        self.assertIsNone(rm.detect_kind([]))


class FrameScriptContract(unittest.TestCase):
    """The frame script finds lines and rows by position, so the order must match what render_chart.py emits."""

    def load(self, name):
        sp = ROOT / "examples" / f"{name}_spec.json"
        spec = json.loads(sp.read_text(encoding="utf-8"))
        return (spec,) + rc.load(spec, sp.parent)

    def test_lines_layout(self):
        spec, d, series, benches, base, end, start, _ = self.load("chart_lines")
        html = rc.build_html(spec, d, series, benches, base, end, start, "en")
        data = rm.motion_data(spec, d, series, benches, base, end, start, "en")
        self.assertEqual(data["mode"], "lines")
        main = re.search(r'<svg id="s0".*?</svg>', html).group(0)
        strokes = re.findall(r'<path d="[^"]*" fill="none" stroke="([^"]+)"', main)
        col = rc.Ctx(spec, d, series, benches, base, end, start, "en", "light").col
        self.assertEqual(strokes, [col[s] for s in data["pathOrder"]])
        rows = re.findall(r'<tr class="[^"]*"><td><svg[^>]*><line[^>]*stroke="([^"]+)"', html)
        self.assertEqual(rows, [col[s] for s in data["rowOrder"]])
        for s in series + benches:
            self.assertEqual(len(data["series"][s.sym]["idx"]), len(s.dates))
        self.assertTrue(all(data["series"][b.sym]["na"] for b in benches))

    def test_multiples_layout(self):
        spec, d, series, benches, base, end, start, _ = self.load("chart_multiples")
        html = rc.build_html(spec, d, series, benches, base, end, start, "en")
        data = rm.motion_data(spec, d, series, benches, base, end, start, "en")
        self.assertEqual(data["mode"], "multiples")
        headers = re.findall(r'font-weight="700"[^>]*>([^<]+)</text>', re.search(r'<svg id="sm".*?</svg>', html).group(0))
        self.assertEqual(headers, data["order"])


class RowScriptContract(unittest.TestCase):
    """The row script animates every tbody row, numbers with a decimal point, .bar widths and the .cum column."""
    NUM = re.compile(r"^([^\d(\-]*)(\(?)(-?)(\d[\d,]*\.(\d+))(\)?)(%?)$")   # same pattern as ROWS_JS

    def test_pattern_matches_rows_js(self):
        self.assertIn("/" + self.NUM.pattern + "/", rm.ROWS_JS)

    def test_number_formats(self):
        for text, parts in [("12.8", ("", "", "", "12.8", "")), ("-3.0", ("", "", "-", "3.0", "")), ("1,234.56", ("", "", "", "1,234.56", "")),
                            ("(5.2)%", ("", "(", "", "5.2", "%")), ("USD 99.89", ("USD ", "", "", "99.89", ""))]:
            m = self.NUM.match(text)
            self.assertIsNotNone(m, text)
            self.assertEqual((m[1], m[2], m[3], m[4], m[7]), parts)
        for text in ("12", "1,250", "NA", "2026-10-02", "Acme (ACRB)", ""):   # ranks, share counts and text are not counted up
            self.assertIsNone(self.NUM.match(text), text)

    def test_holdings_markup(self):
        data = json.loads((ROOT / "examples" / "etf_holdings_swap.json").read_text(encoding="utf-8"))
        html = rh.build_html(data, "en")
        body = re.search(r"<tbody>(.*)</tbody>", html).group(1)
        for row in re.findall(r"<tr>(.*?)</tr>", body):
            self.assertRegex(row, r'<td class="num">[\d.]+</td><td class="num cum">[\d.]+</td>')   # weight, then the running total
            self.assertRegex(row, r'<i class="fp" style="width:[\d.]+%"></i><i class="fs" style="width:[\d.]+%"></i>')

    def test_table_markup(self):
        spec = json.loads((ROOT / "examples" / "watchlist_spec.json").read_text(encoding="utf-8"))
        html = rt.build_html(spec, "en")
        rows = re.findall(r"<tr class=\"[^\"]*\">(.*?)</tr>", re.search(r"<tbody>(.*)</tbody>", html, re.S).group(1))
        self.assertEqual(len(rows), len(spec["rows"]))


if __name__ == "__main__":
    unittest.main()
