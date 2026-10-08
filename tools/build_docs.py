"""Generate README.md, README.zh-Hant.md, README.ja.md, README.fr.md and docs/index.html from tools/docs_content.py.

    python3 tools/build_docs.py            # write the files
    python3 tools/build_docs.py --check    # exit 1 if any generated file is out of date (the unit tests do this too)

README.zh-CN.md is a hand-written pointer to the Traditional Chinese README and is not generated.
"""
import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from docs_content import C, PROMPT  # noqa: E402

SLUG = "imoneys10k/schwab-table"
SITE = "https://imoneys10k.github.io/schwab-table/"
BLOB = f"https://github.com/{SLUG}/blob/main/"
TREE = f"https://github.com/{SLUG}/tree/main/"
LANGS = ["en", "zh", "ja", "fr"]
README = {"en": "README.md", "zh": "README.zh-Hant.md", "ja": "README.ja.md", "fr": "README.fr.md"}
LANG_NAME = {"en": "English", "zh": "繁體中文", "ja": "日本語", "fr": "Français"}
SKILL_DOC = {"en": "SKILL.en.md", "zh": "SKILL.md", "ja": "SKILL.en.md", "fr": "SKILL.en.md"}

# (image name on the site, source file, example links for the style table)
GALLERY = ["examples/neural9_en.png", "examples/watchlist_zh.png", "examples/chart_lines_en.png", "examples/chart_multiples_zh.png",
           "examples/morgan_zh.png", "examples/blackstone_zh.png", "examples/ibkr_zh.png",
           "examples/earnings/aapl_2025q3_zh.png", "examples/earnings/aapl_2025q4_zh.png", "examples/holdings_en.png"]
STYLE_EXAMPLES = ["neural9", "holdings", "watchlist", "morgan", "blackstone", "ibkr"]

BADGES = " ".join([
    '<a href="LICENSE"><img alt="MIT License" src="https://img.shields.io/badge/License-MIT-2a78d6?style=flat-square"></a>',
    f'<a href="https://github.com/{SLUG}/actions/workflows/install-test.yml"><img alt="install test" src="https://img.shields.io/github/actions/workflow/status/{SLUG}/install-test.yml?branch=main&style=flat-square&label=install%20test"></a>',
    f'<a href="https://github.com/{SLUG}/actions/workflows/tests.yml"><img alt="tests" src="https://img.shields.io/github/actions/workflow/status/{SLUG}/tests.yml?branch=main&style=flat-square&label=tests"></a>',
    f'<a href="https://github.com/{SLUG}/releases"><img alt="release" src="https://img.shields.io/github/v/release/{SLUG}?style=flat-square&color=1B2A4A"></a>',
    f'<a href="https://github.com/{SLUG}/stargazers"><img alt="stars" src="https://img.shields.io/github/stars/{SLUG}?style=flat-square&color=eda100"></a>',
    '<img alt="Python 3.9+" src="https://img.shields.io/badge/Python-3.9%2B-1baf7a?style=flat-square">',
    '<img alt="macOS, Linux, Windows" src="https://img.shields.io/badge/macOS%20%C2%B7%20Linux%20%C2%B7%20Windows-supported-ACDCEC?style=flat-square&labelColor=1B2A4A">',
    '<img alt="Agent Skills" src="https://img.shields.io/badge/Agent-Skills-eb6834?style=flat-square">',
])


def check_content():
    base = C["en"]
    for lang in LANGS:
        c = C[lang]
        if set(c) != set(base):
            raise SystemExit(f"docs_content: language {lang} keys differ: {sorted(set(c) ^ set(base))}")
        for k, v in base.items():
            if isinstance(v, (list, tuple)) and len(c[k]) != len(v):
                raise SystemExit(f"docs_content: {lang}.{k} has {len(c[k])} items, English has {len(v)}")
        if lang not in PROMPT:
            raise SystemExit(f"docs_content: no install prompt for {lang}")
    if len(base["gallery"]) != len(GALLERY):
        raise SystemExit("docs_content: gallery captions and GALLERY images differ in length")
    if len(base["style_rows"]) != len(STYLE_EXAMPLES):
        raise SystemExit("docs_content: style rows and STYLE_EXAMPLES differ in length")


def slug(heading):
    """GitHub's heading anchor: lower-case, drop emoji and punctuation, spaces to hyphens."""
    return re.sub(r"[^\w\s-]", "", heading.lower(), flags=re.UNICODE).replace(" ", "-")


def md_table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------------------------------
def readme(lang):
    c = C[lang]
    nav = " · ".join(f"**{LANG_NAME[l]}**" if l == lang else f"[{LANG_NAME[l]}]({README[l]})" for l in LANGS)
    a_install, a_gallery = slug("🚀 " + c["h_install"]), slug("🎨 " + c["h_gallery"])
    L = c["links"]
    header = (f'<div align="center">\n\n<img src="assets/banner.png" alt="schwab-table" width="100%">\n\n**{c["tagline"]}**\n\n{nav}\n\n<p>{BADGES}</p>\n\n'
              f'<p><a href="#{a_install}"><b>{L[0]}</b></a> · <a href="#{a_gallery}"><b>{L[1]}</b></a> · <a href="{SITE}"><b>{L[2]}</b></a> · '
              f'<a href="{SITE}earnings/"><b>{L[3]}</b></a> · <a href="{SKILL_DOC[lang]}"><b>{L[4]}</b></a></p>\n\n</div>\n')

    cards = []
    for i in range(0, len(c["cards"]), 2):
        cards.append("<tr>" + "".join(f'<td width="50%" valign="top"><h3>{e} {t}</h3><p>{d}</p></td>' for e, t, d in c["cards"][i:i + 2]) + "</tr>")
    highlights = "<table>\n" + "\n".join(cards) + "\n</table>"

    cells = []
    for img, (cap, tag) in zip(GALLERY, c["gallery"]):
        cells.append(f'<td width="50%" align="center"><img src="{img}" alt="{cap}"><br><sub><b>{cap}</b> · {tag}</sub></td>')
    gallery = "<table>\n" + "\n".join("<tr>" + "".join(cells[i:i + 2]) + "</tr>" for i in range(0, len(cells), 2)) + "\n</table>"

    f = c["flow"]
    flow = f'''```mermaid
flowchart LR
  A["{f[0]}"] --> B["{f[1]}"]
  B --> C["{f[2]}"]
  B --> F["{f[3]}"]
  C --> D["{f[4]}"]
  F --> G["{f[5]}"]
  D --> E["{f[6]}"]
  G --> E
  classDef n fill:#ACDCEC,stroke:#1B2A4A,color:#1B2A4A,stroke-width:1px;
  class A,B,C,D,E,F,G n;
```'''

    flags = [("`--dir PATH`", "`-Dir PATH`"), ("`--ref TAG`", "`-Ref TAG`"), ("`--skip-deps`", "`-SkipDeps`"), ("`--uninstall`", "`-Uninstall`")]
    opts = md_table(c["opt_head"], [(a, b, e) for (a, b), e in zip(flags, c["opts"])])

    style_rows = []
    for (name, what), ex in zip(c["style_rows"], STYLE_EXAMPLES):
        style_rows.append((name, what, f"[EN](examples/{ex}_en.png) · [繁體中文](examples/{ex}_zh.png)"))
    styles_table = md_table(c["style_head"], style_rows)
    sc = c["style_cmds"]
    style_cmds = (f"```bash\npython3 render_table.py examples/watchlist_spec.json out/watchlist     {sc[0]}\n"
                  f"python3 render_table.py examples/morgan_spec.json out/matrix           {sc[1]}\n"
                  f"python3 prices_to_table.py data/prices.json data/matrix.json --style morgan   {sc[2]}\n"
                  "python3 render_table.py data/matrix.json out/matrix\n```")

    layout = md_table(c["layout_head"], c["layout_rows"])
    route = md_table(c["route_head"], c["route_rows"])
    chart_cmds = ("```bash\npython3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 -o data/watch.json\n"
                  "python3 fetch_prices.py 7203.T 0700.HK SAP.DE 600519.SS --start 2026-08-01 --benchmark none -o data/global.json\n"
                  "python3 render_chart.py examples/chart_lines_spec.json out/chart\n```")
    earn_cmd = "```bash\npython3 quarterly_earnings.py AAPL --period FY2025Q3 -o out/aapl_q3\n```"
    files = "\n".join(f"- {n}: {d}" for n, d in c["files"])
    manual_cmds = ("```bash\npip install -r requirements.txt && playwright install chromium\n"
                   "python3 render_table.py examples/neural9_spec.json out/neural9\n"
                   "python3 render_table.py examples/morgan_spec.json out/matrix\n"
                   "python3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 -o data/watch.json\n"
                   "python3 render_chart.py examples/chart_lines_spec.json out/chart --theme dark --pdf\n"
                   "python3 csv_to_prices.py 0700.HK=tencent.csv --benchmark HSI=hsi.csv -o data/hk.json\n"
                   "python3 quarterly_earnings.py AAPL --period FY2025Q3 -o out/aapl_q3\n```")

    parts = [
        header, c["intro"] + "\n",
        f"## ✨ {c['h_high']}\n\n{highlights}\n",
        f"## 🎨 {c['h_gallery']}\n\n{gallery}\n\n<sub>{c['gallery_note']}</sub>\n",
        f"## 🔄 {c['h_flow']}\n\n{flow}\n",
        f"## 🚀 {c['h_install']}\n\n{c['install_intro']}\n\n{c['tip']}\n\n### {c['h_agent']}\n\n{c['agent_intro']}\n\n```text\n{PROMPT[lang]}\n```\n\n"
        f"### {c['h_self']}\n\nmacOS / Linux:\n\n```bash\ncurl -fsSL https://raw.githubusercontent.com/{SLUG}/main/install.sh | sh\n```\n\n"
        f"Windows (PowerShell):\n\n```powershell\nirm https://raw.githubusercontent.com/{SLUG}/main/install.ps1 | iex\n```\n\n{c['install_note']}\n\n{opts}\n\n"
        f"{c['pipe_note']}\n\n{c['update_note']}\n\n{c['trouble']}\n",
        f"## 💬 {c['h_using']}\n\n{c['using_intro']}\n\n" + "\n".join(f"- {u}" for u in c["using"]) + "\n",
        f"## 🧩 {c['h_styles']}\n\n{c['styles_intro']}\n\n{styles_table}\n\n{style_cmds}\n\n{c['style_note']}\n",
        f"## 📊 {c['h_charts']}\n\n{c['charts_intro']}\n\n{layout}\n\n{c['layout_auto']}\n\n{route}\n\n" + "\n".join(f"- {b}" for b in c["chart_bullets"]) + f"\n\n{chart_cmds}\n",
        f"## 🧾 {c['h_earn']}\n\n{c['earn_intro']}\n\n" + "\n".join(f"- {p}" for p in c["earn_points"]) + f"\n\n{earn_cmd}\n\n{c['earn_links']}\n",
        f"## 🔍 {c['h_rules']}\n\n" + "\n".join(f"- {r}" for r in c["rules"]) + "\n",
        f"<details>\n<summary><b>{c['sum_files']}</b></summary>\n\n{files}\n\n</details>\n",
        f"<details>\n<summary><b>{c['sum_manual']}</b></summary>\n\n{c['manual_intro']}\n\n{manual_cmds}\n\n{c['manual_after']}\n\n{c['manual_fetch']}\n\n{c['manual_fonts']}\n\n</details>\n",
        f"## 🧪 {c['h_test']}\n\n{c['test_text']}\n",
        f"## 📌 {c['h_disc']}\n\n{c['disc']}\n",
        f"## 📄 {c['h_lic']}\n\n[MIT](LICENSE)\n\n<div align=\"center\"><sub>{c['star']}</sub></div>\n",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------------------------------------------------
def inline(md):
    """Tiny Markdown subset for the website: **bold**, `code` and [text](link); relative links point at the GitHub repository."""
    s = html.escape(md, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)

    def link(m):
        text, url = m.group(1), m.group(2)
        if not url.startswith("http"):
            url = (TREE if url.endswith("/") else BLOB) + url
        return f'<a href="{url}">{text}</a>'
    return re.sub(r"\[(.+?)\]\((.+?)\)", link, s)


def site_data():
    data = {}
    for lang in LANGS:
        c = C[lang]
        chips = [(re.sub(r"`", "", n), w) for n, w in c["style_rows"]] + [(re.sub(r"`", "", r[0]), f"{r[1]} ({r[2]})") for r in c["layout_rows"]]
        data[lang] = {
            "hero_a": c["hero_a"], "hero_b": c["hero_b"], "sub": c["site_sub"], "cta1": c["cta1"], "cta2": c["cta2"], "cta3": c["cta3"],
            "t_features": c["h_high"], "cards": [list(x) for x in c["cards"]], "t_gallery": c["h_gallery"],
            "gallery": [list(x) for x in c["gallery"]], "gallery_note": c["gallery_note"], "t_modes": c["t_modes"], "chips": [list(x) for x in chips],
            "t_earn": c["t_earn"], "earn_intro": inline(c["earn_intro"]), "earn_points": [inline(p) for p in c["earn_points"]],
            "earn_btn": c["earn_btn"], "earn_doc": inline(c["earn_links"].split(" · ")[1]),
            "t_data": c["t_data"], "route_head": c["route_head"], "route_rows": [[inline(x) for x in r] for r in c["route_rows"]],
            "rules": [inline(r) for r in c["rules"][:4]],
            "t_install": c["h_install"], "tab_unix": c["tab_unix"], "tab_win": c["tab_win"], "or_agent": c["or_agent"], "prompt": PROMPT[lang],
            "copy": c["copy"], "copied": c["copied"], "foot": c["foot"], "docs_label": c["docs_label"],
        }
    return data


def site():
    check_content()
    template = (Path(__file__).resolve().parent / "site_template.html").read_text(encoding="utf-8")
    js = json.dumps(site_data(), ensure_ascii=False).replace("</", "<\\/")
    docs_links = " · ".join(f'<a href="{BLOB}{README[l]}">{LANG_NAME[l]}</a>' for l in LANGS)
    return (template.replace("/*DATA*/", js).replace("/*IMGS*/", json.dumps([Path(g).stem for g in GALLERY]))
            .replace("<!--DOCS_LINKS-->", docs_links))


def render_all():
    check_content()
    out = {README[l]: readme(l) for l in LANGS}
    out["docs/index.html"] = site()
    return out


def image_copies():
    """Files the website needs next to index.html: (source, destination) relative to the repository root."""
    pairs = [(g, f"docs/img/{Path(g).name}") for g in GALLERY]
    pairs.append(("assets/social-preview.png", "docs/img/social-preview.png"))
    return pairs


def stale():
    names = []
    for name, text in render_all().items():
        p = ROOT / name
        if not p.exists() or p.read_text(encoding="utf-8") != text:
            names.append(name)
    for src, dst in image_copies():
        p = ROOT / dst
        if not p.exists() or p.read_bytes() != (ROOT / src).read_bytes():
            names.append(dst)
    return names


def main():
    if "--check" in sys.argv:
        names = stale()
        if names:
            print("out of date (run python3 tools/build_docs.py):", ", ".join(names))
            raise SystemExit(1)
        print("docs are up to date")
        return
    for name, text in render_all().items():
        (ROOT / name).write_text(text, encoding="utf-8")
        print("wrote", name)
    (ROOT / "docs" / "img").mkdir(parents=True, exist_ok=True)
    for src, dst in image_copies():
        shutil.copyfile(ROOT / src, ROOT / dst)
    # drop site images that are no longer referenced
    keep = {Path(d).name for _, d in image_copies()}
    for p in (ROOT / "docs" / "img").glob("*.png"):
        if p.name not in keep:
            p.unlink()
            print("removed unused", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
