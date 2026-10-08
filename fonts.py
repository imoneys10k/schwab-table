"""Embed the bundled Inter font (SIL OFL, see fonts/OFL.txt) into generated HTML as a data URI,
so tables and charts look the same on every machine. Chinese text falls back to the system CJK font."""
import base64
from pathlib import Path

_FONT = Path(__file__).resolve().parent / "fonts" / "inter-latin-wght-normal.woff2"


def font_face_css(style="schwab"):
    registry = {
        "schwab": ("Inter", _FONT, "woff2", "100 900"),
        "morgan": ("Source Sans 3", _FONT.parent / "SourceSans3VF-Upright.ttf", "truetype", "200 900"),
        "blackstone": ("Source Sans 3", _FONT.parent / "SourceSans3VF-Upright.ttf", "truetype", "200 900"),
        "ibkr": ("Droid Sans", _FONT.parent / "DroidSans.ttf", "truetype", "400"),
    }
    family, path, fmt, weight = registry[style]
    if not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = "woff2" if fmt == "woff2" else "ttf"
    return (f"@font-face{{font-family:'{family}';font-style:normal;font-weight:{weight};"
            f"src:url(data:font/{mime};base64,{b64}) format('{fmt}');}}")
