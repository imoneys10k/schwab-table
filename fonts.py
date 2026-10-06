"""Embed the bundled Inter font (SIL OFL, see fonts/OFL.txt) into generated HTML as a data URI,
so tables and charts look the same on every machine. Chinese text falls back to the system CJK font."""
import base64
from pathlib import Path

_FONT = Path(__file__).resolve().parent / "fonts" / "inter-latin-wght-normal.woff2"


def font_face_css():
    if not _FONT.exists():
        return ""
    b64 = base64.b64encode(_FONT.read_bytes()).decode("ascii")
    return ("@font-face{font-family:'Inter';font-style:normal;font-weight:100 900;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
