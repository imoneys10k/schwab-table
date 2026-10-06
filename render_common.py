"""Shared by render_table.py and render_chart.py: colour themes, venv switching, PNG / PDF rendering."""
import asyncio
import os
import sys
from pathlib import Path

# Series colours are the first five validated categorical slots, in fixed order (dark values are the palette's dark steps).
THEMES = {
    "light": dict(bg="#fff", border="#D0D0D0", band="#ACDCEC", band_text="#1B2A4A", grid="#E4E4E4", axis="#9A9A9A", muted="#6B6B6B", ink="#2B2B2B",
                  rule="#D9D9D9", foot="#6B6B6B", foot_b="#555", tbl="#595959", stock="#1B2A4A", ring="#fff", dd_fill="#ACDCEC", dd_op=".65",
                  ser=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"], bench=["#595959", "#8E8E8E"], bench_multi="#B5B5B5"),
    "dark": dict(bg="#1a1a19", border="#3A3A37", band="#1F3A52", band_text="#DCEBF7", grid="#2C2C2A", axis="#5C5B57", muted="#A6A59B", ink="#EDEDEA",
                 rule="#34342F", foot="#9A998F", foot_b="#C3C2B7", tbl="#C3C2B7", stock="#9EC5F4", ring="#1a1a19", dd_fill="#2B5A7A", dd_op=".55",
                 ser=["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"], bench=["#C3C2B7", "#8A897F"], bench_multi="#6E6D66"),
}


def reexec_in_venv():
    """If install.sh / install.ps1 created a .venv next to the scripts, run again with its Python."""
    here = Path(__file__).resolve().parent
    venv = here / ".venv"
    py = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if py.exists() and Path(sys.prefix).resolve() != venv.resolve() and not os.environ.get("SCHWAB_TABLE_REEXEC"):
        os.environ["SCHWAB_TABLE_REEXEC"] = "1"
        sys.stdout.flush()
        if os.name == "nt":  # os.execv on Windows detaches from the console; wait for the child instead
            import subprocess
            sys.exit(subprocess.call([str(py), *sys.argv]))
        os.execv(str(py), [str(py), *sys.argv])


async def _render(htmls, prefix, scale, png, pdf):
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        reexec_in_venv()
        sys.exit("error: playwright is not installed. Run: pip install playwright && playwright install chromium\n"
                 "(or pass --no-png to write HTML only)")
    async with async_playwright() as p:
        try:
            b = await p.chromium.launch()
        except Exception as e:
            if "Executable doesn't exist" in str(e):
                sys.exit("error: Chromium is not installed. Run: playwright install chromium")
            raise
        for lang, html in htmls.items():
            pg = await b.new_page(device_scale_factor=scale, viewport={"width": 800, "height": 700})
            await pg.set_content(html)
            await pg.evaluate("document.fonts.ready")
            loc = pg.locator("#wrap")
            if png:
                await loc.screenshot(path=f"{prefix}_{lang}.png")
            if pdf:
                box = await loc.bounding_box()
                await pg.pdf(path=f"{prefix}_{lang}.pdf", width=f"{box['width']}px", height=f"{box['height'] + 1}px", print_background=True, page_ranges="1")
            await pg.close()
        await b.close()


def render_files(htmls, prefix, scale=2, png=True, pdf=False):
    """htmls = {lang: html}; writes {prefix}_{lang}.png and/or .pdf (needs Playwright + Chromium)."""
    asyncio.run(_render(htmls, prefix, scale, png, pdf))
    for lang in htmls:
        if png:
            print(f"wrote {prefix}_{lang}.png")
        if pdf:
            print(f"wrote {prefix}_{lang}.pdf")
