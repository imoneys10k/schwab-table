"""All text shown in the READMEs and on the website, per language. Edit here, then run: python3 tools/build_docs.py

Languages: en, zh (Traditional Chinese), ja, fr. Every language must define the same keys; the build fails otherwise.
Commands, file names and URLs are shared by the build script and are not translated.
"""

PROMPT = {
    "en": """Install the skills from https://github.com/imoneys10k/schwab-table for me.
Detect my operating system. On macOS or Linux, run:
  curl -fsSL https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.sh | sh
On Windows, in PowerShell, run:
  irm https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.ps1 | iex
If I use an agent other than Claude, install into that agent's skills folder instead
(macOS/Linux: add `--dir <path>` after `sh -s --`; Windows: save install.ps1 and run it with -Dir <path>).
When it finishes, confirm that "Render OK" was printed, then tell me to restart so the skills load.""",
    "zh": """請幫我安裝 https://github.com/imoneys10k/schwab-table 裡的 skill。
先判斷我的作業系統。macOS 或 Linux 執行：
  curl -fsSL https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.sh | sh
Windows 在 PowerShell 執行：
  irm https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.ps1 | iex
如果我用的不是 Claude，請裝到那個 Agent 自己的 skills 目錄
（macOS/Linux 在 `sh -s --` 後面加 `--dir <路徑>`；Windows 先儲存 install.ps1，再用 -Dir <路徑> 執行）。
裝完確認輸出了 "Render OK"，然後提醒我重新啟動，讓 skill 生效。""",
    "ja": """https://github.com/imoneys10k/schwab-table のスキルをインストールしてください。
まず私の OS を判別してください。macOS または Linux では次を実行します。
  curl -fsSL https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.sh | sh
Windows では PowerShell で次を実行します。
  irm https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.ps1 | iex
Claude 以外のエージェントを使っている場合は、そのエージェントの skills フォルダにインストールしてください
（macOS/Linux は `sh -s --` の後ろに `--dir <パス>` を付けます。Windows は install.ps1 を保存して -Dir <パス> 付きで実行します）。
完了したら "Render OK" と表示されたことを確認し、スキルを読み込むために再起動するよう伝えてください。""",
    "fr": """Installe pour moi les skills de https://github.com/imoneys10k/schwab-table.
Détecte d'abord mon système d'exploitation. Sous macOS ou Linux, exécute :
  curl -fsSL https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.sh | sh
Sous Windows, dans PowerShell, exécute :
  irm https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.ps1 | iex
Si j'utilise un autre agent que Claude, installe-les plutôt dans le dossier skills de cet agent
(macOS/Linux : ajoute `--dir <chemin>` après `sh -s --` ; Windows : enregistre install.ps1 et lance-le avec -Dir <chemin>).
Une fois terminé, vérifie que « Render OK » s'est affiché, puis dis-moi de redémarrer pour que les skills soient chargés.""",
}

C = {}

# =====================================================================================================================
C["en"] = dict(
    tagline="Research-desk tables, price charts and quarterly earnings reviews for your AI agent.",
    links=["🚀 Install", "🎨 Gallery", "🌐 Website", "🧾 Earnings demo", "📘 Skill doc"],
    intro=("Two Claude skills in one repository. **schwab-performance-table** turns a stock list, a brokerage holdings screenshot, price data or your own "
           "CSV into research-desk tables (Schwab, Morgan, Blackstone and IBKR layouts) and into price charts with drawdown and log scale. "
           "**quarterly-earnings-review** checks a company's quarterly filing and produces an HSBC-style earnings table with source-backed commentary. "
           "Everything is rendered in English and Traditional Chinese, as PNG plus self-contained HTML."),
    h_high="Highlights",
    cards=[
        ("🎯", "Four report layouts", "Schwab, Morgan, Blackstone and IBKR styles with explicit column schemas. Independent templates, not reports issued by those institutions."),
        ("📊", "Tables, charts, earnings", "Ranking, holdings and watchlist tables; line charts and small multiples with drawdown and log scale; HSBC-style quarterly earnings."),
        ("🌏", "English and Traditional Chinese", "Every output in both languages: 2x PNG and self-contained HTML, with an optional dark theme and PDF."),
        ("🔒", "Sources always shown", "Nasdaq and Shanghai/Shenzhen exchange closes, clearly labelled Yahoo data for other markets, SEC and Apple filings for earnings. Missing data is NA, never invented."),
        ("🤖", "One-line agent install", "Paste a prompt into Claude Code or Codex. Works on macOS, Linux and Windows, and installs both skills."),
        ("🧪", "Tested", "Known-answer unit tests, CI on three operating systems, a live data smoke test and a first round of agent evals."),
    ],
    h_gallery="Gallery",
    gallery=[("Ranking table", "EN"), ("Watchlist table", "繁體中文"), ("Line chart with drawdown", "EN"), ("Small multiples, log scale", "繁體中文"),
             ("Morgan-style matrix", "繁體中文"), ("Blackstone-style performance", "繁體中文"), ("IBKR-style holdings", "繁體中文"),
             ("HSBC quarterly earnings, AAPL Q3", "繁體中文"), ("HSBC quarterly earnings, AAPL Q4", "繁體中文"), ("Holdings table", "EN")],
    gallery_note="The earnings examples use Apple's official filings and the ranking table a public Charles Schwab chart. Everything else uses fictional companies and synthetic data.",
    h_flow="How it works",
    flow=["📝 Tickers, screenshot, CSV<br/>or ticker + quarter", "🤖 Claude + skills", "🏛 Prices: Nasdaq, SSE/SZSE,<br/>Yahoo (labelled), your CSV",
          "📑 Filings: Apple PDFs,<br/>SEC facts, your imports", "🖨 render_table<br/>render_chart", "🖨 quarterly_earnings", "🖼 PNG + HTML<br/>EN · 繁體中文"],
    h_install="Install",
    install_intro="Works on macOS, Linux and Windows. You need Python 3.9+ (to render); git is optional. The installer registers both skills.",
    tip="💡 **Easiest way:** paste the prompt below into your AI agent and it installs everything for you.",
    h_agent="🤖 Let your AI agent install it",
    agent_intro="Paste this to Claude Code, Codex or any other coding agent:",
    h_self="💻 Or run it yourself",
    install_note=("The installer puts the main skill in `~/.claude/skills/schwab-performance-table` (`%USERPROFILE%\\.claude\\skills\\...` on Windows), "
                  "creates a private Python virtual environment inside it, installs the dependencies and Chromium (about 100 MB), registers "
                  "`quarterly-earnings-review` beside it, and renders every table style, a chart and an earnings table as a smoke test. "
                  "It prints `Render OK` when everything works. Restart Claude afterwards so the skills are picked up. "
                  "To read a script before running it, open [install.sh](install.sh) or [install.ps1](install.ps1)."),
    opt_head=["Option (macOS / Linux)", "Option (Windows)", "Effect"],
    opts=["Install somewhere else (for example another agent's skills folder). `CLAUDE_SKILLS_DIR` changes the default root.",
          "Install a tag or branch instead of `main`, e.g. `v0.6.1`, to pin a version. Run the installer again without it to return to `main`.",
          "Skip Python, Playwright and Chromium (only fetch and register the files).",
          "Delete the installed skill folder and the earnings skill registered by it."],
    pipe_note="When piping, pass options with `sh -s --`, for example `curl -fsSL .../install.sh | sh -s -- --dir ~/my-skills/schwab`. On Windows, save `install.ps1` and run `.\\install.ps1 -Dir C:\\path`.",
    update_note="**Update:** run the same command again. **Uninstall:** run it with `--uninstall` (`-Uninstall` on Windows).",
    trouble="**Troubleshooting:** on Debian/Ubuntu install `python3-venv` first. On Linux, if Chromium fails to start, run `sudo <install folder>/.venv/bin/python -m playwright install-deps chromium`. On a minimal Linux server install a CJK font (`sudo apt install fonts-noto-cjk`), otherwise Chinese text renders as boxes.",
    h_using="Using it with Claude",
    using_intro="Once installed, just ask in plain language, for example:",
    using=["Make a performance table for NVDA, AMD and MU.",
           "Turn this holdings screenshot into a Schwab-style table. (attach the screenshot)",
           "Chart NVDA, MU and AAPL for this year against the S&P 500.",
           "Compare these six stocks from March to June on a log scale.",
           "Show AAPL, MSFT and NVDA in a Morgan-style return and risk matrix.",
           "Chart 7203.T, 0700.HK and 600519.SS year to date.",
           "Review AAPL FY2025Q3 in an HSBC-style table."],
    h_styles="Table styles",
    styles_intro="Four layouts, chosen with `--style` (or `spec.style`; the default is Schwab). They are independent templates, not reports issued by or affiliated with the named institutions.",
    style_head=["Style", "What it shows", "Example"],
    style_rows=[("Schwab · ranking", "YTD plus rank in the S&P 500 and NASDAQ (mode A)"), ("Schwab · holdings", "Open P/L %, today's P/L, average cost, shares, from a screenshot or export (mode B)"),
                ("Schwab · watchlist", "Tickers only: YTD, 1-month, 1-year, last close (mode C)"), ("Morgan", "Two periods × return, volatility and drawdown"),
                ("Blackstone", "Industry or strategy groups, two return periods"), ("IBKR", "Brokerage fields, market values, weights and supplied exposure")],
    style_cmds=["# Schwab (default)", "# or --style morgan | blackstone | ibkr", "# build a matrix from fetched prices"],
    style_note=("Each template has explicit column schemas; passing a five-column watchlist to a seven- or nine-column report does not invent missing facts. "
                "Schwab tables and charts keep light and dark modes; the other templates are calibrated for white paper. See the "
                "[template guide](references/institutional-tables.md) for schemas, source samples and font substitutions."),
    h_charts="Price charts",
    charts_intro="Chart up to 9 symbols over any period (default: year to date) with a drawdown panel and a summary table.",
    layout_head=["Layout", "Content", "Use for"],
    layout_rows=[("`lines`", "Line chart, drawdown panel, summary table", "2–5 symbols"), ("`multiples`", "One small chart per symbol on a shared scale, drawdown strip under each", "6–9 symbols")],
    layout_auto="`layout: auto` picks one by symbol count.",
    route_head=["Symbols", "Source", "Notes"],
    route_rows=[("US stocks, ETFs, Nasdaq indexes (`NVDA`, `BRK.B`, `SPY`, `COMP`)", "Nasdaq official closes", "Split-adjusted price return, about 10 years of history"),
                ("Shanghai / Shenzhen (`600519.SS`, `000001.SZ`)", "Exchange websites", "Unadjusted closes; Shenzhen history is limited"),
                ("Other exchanges and indexes (`7203.T`, `0700.HK`, `SAP.DE`, `^N225`)", "Yahoo Finance", "Clearly labelled as aggregated data; use the exchange suffix"),
                ("Your own files", "`csv_to_prices.py`", "Any market; an adjusted-close CSV gives a labelled total-return chart")],
    chart_bullets=["**Benchmark:** SPY by default (labelled as a proxy for the S&P 500), up to two benchmarks (`--benchmark SPY,COMP`), or `--benchmark none`.",
                   "**Axis:** one y-axis, indexed to 100 at the start. It switches to a log scale automatically when the range is wide (or set `y_scale`).",
                   "**Options:** `--theme dark`, `--pdf`, custom line colours, and hover tooltips in the HTML files."],
    h_earn="Quarterly earnings review",
    earn_intro="Ask “Review AAPL FY2025Q3 in an HSBC-style table.” The **quarterly-earnings-review** skill verifies the fiscal dates and the primary filing, computes single-quarter, year-over-year and quarter-over-quarter values, and adds commentary that cites its sources. Output is an English and Traditional Chinese PNG + HTML, plus the raw facts and an audit ledger.",
    earn_points=["**Sources:** Apple's official financial PDFs (verified live for FY2025Q3 and FY2025Q4); other US-GAAP companies through SEC Company Facts (the parser is covered by fixed fixtures, live access can be refused); other markets through verified official reports imported with `--facts`.",
                 "**Fiscal quarters, not calendar quarters:** the table states the real period dates. Annual or cumulative figures are never relabelled as quarterly facts; missing data stays NA.",
                 "**Commentary:** every comment cites a source ledger ID. No beat/miss claim without consensus evidence; the facts are never overwritten by the analysis."],
    earn_links="[Try the two-quarter demo](https://imoneys10k.github.io/schwab-table/earnings/) · [Usage and source coverage](EARNINGS.md, in Traditional Chinese) · [Skill](skills/quarterly-earnings-review/SKILL.md)",
    h_rules="Data and honesty rules",
    rules=["**Sources are always printed** in the footnote with the cutoff and retrieval dates. Unavailable history is reported, never silently shortened.",
           "**`null` is not zero.** Missing data renders as `NA`; nothing is filled from memory or guessed.",
           "**Price return only from automatic sources.** Nasdaq dividend amounts are not split-adjusted and ETFs have none, so total return needs your own adjusted-close CSV.",
           "**Yahoo is labelled as aggregated data**, not as exchange-published closes. A-share website prices are unadjusted; the tools warn about corporate-action distortion.",
           "**Hong Kong and other markets need the exchange suffix** (`0700.HK`); bare numeric codes are ambiguous and rejected.",
           "Details for agents are in [SKILL.md](SKILL.md) (Traditional Chinese) and [SKILL.en.md](SKILL.en.md) (English)."],
    sum_files="📁 Files",
    files=[("`SKILL.md`, `SKILL.en.md`", "The skill Claude loads (Traditional Chinese) and its English translation"),
           ("`skills/quarterly-earnings-review/`", "The earnings skill, registered beside the main skill by the installers"),
           ("`install.sh`, `install.ps1`, `install_earnings_skill.py`", "One-click installers for macOS / Linux and Windows, and the earnings skill registration"),
           ("`render_table.py`, `institutional_tables.py`, `prices_to_table.py`", "Table renderer and its four styles; builds Morgan / Blackstone specs from fetched prices"),
           ("`fetch_prices.py`, `csv_to_prices.py`", "Daily closes from Nasdaq, Shanghai/Shenzhen and Yahoo; conversion of your own CSV files"),
           ("`render_chart.py`, `render_common.py`", "Chart renderer; shared themes and PNG / PDF output"),
           ("`quarterly_earnings.py`, `earnings_core.py`, `earnings_sources.py`, `render_earnings.py`", "Earnings command, audited arithmetic, source adapters and the HSBC-style renderer"),
           ("`localization.py`, `fonts.py`, `fonts/`", "Traditional Chinese conversion; bundled fonts embedded in the HTML (licences included)"),
           ("`references/`, `EARNINGS.md`", "Template guide; earnings usage and source coverage (Traditional Chinese)"),
           ("`examples/`, `docs/`", "Specs and rendered examples (`sample_prices.json` is synthetic); the GitHub Pages site"),
           ("`tests/`, `evals/`", "Unit tests; realistic agent requests, a trigger-test set and results"),
           ("`tools/build_docs.py`", "Generates these READMEs and the website from one content table"),
           ("`requirements.txt`, `CHANGELOG.md`, `CONTRIBUTING.md`, `assets/`", "Dependencies, history, contribution rules, banner and social card")],
    sum_manual="🔧 Manual rendering",
    manual_intro="If you used the installer, the scripts switch to the private virtual environment automatically, so plain `python3 render_table.py ...` works. Otherwise Python 3.9+ is required:",
    manual_after=("Options for both renderers: `--langs en` renders only the listed languages (comma-separated, `zh` is Traditional Chinese and the `_zh` file names are kept), "
                  "`--no-png` writes HTML only and needs no browser, `--scale 3` raises the PNG resolution (default 2, which gives 1520 px wide), `--theme dark` and `--pdf`. "
                  "Missing output folders are created."),
    manual_fetch=("`fetch_prices.py` caches responses for up to 12 hours (`--refresh` bypasses the cache) and reuses a cache only if it already has the newest expected close. "
                  "If the network fails it falls back to the last cache with a warning. `index:COMP` / `etf:SPY` force the asset class when a code is ambiguous. "
                  "Charts take two steps: fetch, then render; pass `--start` / `--end` for a period."),
    manual_fonts=("Fonts: Inter, Source Sans 3 and Droid Sans are bundled and embedded for Latin text; Chinese text uses the system Traditional Chinese font. "
                  "Source-font substitutions are documented in [the template guide](references/institutional-tables.md). Proprietary fonts from reference PDFs or macOS are not distributed."),
    h_test="Tests and evals",
    test_text=("`python3 -m unittest discover -s tests -v` runs known-answer tests for returns, drawdown, volatility, symbol routing, cache freshness, CSV import, table styles and earnings arithmetic. "
               "CI runs them on Ubuntu, macOS and Windows (Python 3.9 and 3.13), regenerates the examples to check they are unchanged, runs a live Nasdaq smoke test, and installs the skills on all three systems. "
               "[evals/](evals/README.md) holds realistic agent requests and the first results. The READMEs and the website are generated by `python3 tools/build_docs.py`, and a test fails if they are out of date."),
    h_disc="Disclaimer",
    disc="This project formats data and does not provide investment advice. Examples use fictional companies and synthetic values unless the gallery note says otherwise. The report layouts are independent templates, not reports issued by the named institutions.",
    h_lic="License",
    star="⭐ If this saves you time, a star helps others find it.",
    # ---- website only
    hero_a="Research-desk tables,", hero_b="charts and earnings reviews.",
    site_sub="Institutional-style tables and price charts, plus HSBC-style quarterly earnings reviews built from primary filings. English and Traditional Chinese, PNG + HTML.",
    cta1="Install in one line", cta2="View on GitHub", cta3="Earnings demo",
    t_modes="Pick a layout",
    t_earn="Quarterly earnings, from the filing",
    earn_btn="Open the demo", t_data="Where the numbers come from",
    tab_unix="macOS / Linux", tab_win="Windows", or_agent="Or let your AI agent do it", copy="Copy", copied="Copied",
    docs_label="Docs", foot="MIT licensed. Illustrative only, not investment advice.",
)

# =====================================================================================================================
C["zh"] = dict(
    tagline="給 AI Agent 用的研報風格表格、走勢圖與季度財報解讀。",
    links=["🚀 安裝", "🎨 效果圖", "🌐 專案網站", "🧾 財報示範", "📘 Skill 文件"],
    intro=("同一個儲存庫裡有兩個 Claude skill。**schwab-performance-table** 把股票清單、券商持倉截圖、價格資料或你自己的 CSV，"
           "做成研報風格的表格（Schwab、摩根士丹利、黑石、IBKR 版式），也能畫帶回撤和對數刻度的走勢圖。"
           "**quarterly-earnings-review** 核對公司的季度財報原件，輸出 HSBC 版式的財報表與有來源支持的解讀。"
           "所有輸出都有繁體中文與英文兩版，格式為 PNG 加獨立的 HTML。"),
    h_high="亮點",
    cards=[
        ("🎯", "四種報表版式", "Schwab、摩根士丹利、黑石與 IBKR 版式，欄位結構明確。這些是獨立的範本，並非上述機構發布的報告。"),
        ("📊", "表格、走勢圖、財報", "排名表、持倉表、自選股表；帶回撤與對數刻度的線圖和小圖矩陣；HSBC 版式的季度財報。"),
        ("🌏", "繁體中文與英文", "每次輸出兩種語言：2x PNG 加獨立 HTML，另可選深色主題與 PDF。"),
        ("🔒", "來源一定標明", "Nasdaq 與上海／深圳交易所收盤價、明確標示的 Yahoo 資料（其他市場）、財報用 SEC 與 Apple 官方文件。缺資料寫 NA，絕不編造。"),
        ("🤖", "一句話讓 Agent 安裝", "把提示詞貼給 Claude Code 或 Codex 即可。支援 macOS、Linux、Windows，兩個 skill 一起裝好。"),
        ("🧪", "有測試", "有標準答案的單元測試、三個作業系統的 CI、即時資料冒煙測試，以及第一輪 Agent 評測。"),
    ],
    h_gallery="效果圖",
    gallery=[("排名表", "EN"), ("自選股表", "繁體中文"), ("帶回撤的線圖", "EN"), ("小圖矩陣（對數刻度）", "繁體中文"),
             ("摩根士丹利矩陣", "繁體中文"), ("黑石分組業績", "繁體中文"), ("IBKR 持倉明細", "繁體中文"),
             ("HSBC 季度財報：AAPL 第三季", "繁體中文"), ("HSBC 季度財報：AAPL 第四季", "繁體中文"), ("持倉表", "EN")],
    gallery_note="財報示例使用 Apple 官方文件，排名表來自 Charles Schwab 公開圖表，其餘示例使用虛構公司與合成資料。",
    h_flow="運作方式",
    flow=["📝 股票代碼、截圖、CSV<br/>或代碼＋季度", "🤖 Claude + skills", "🏛 價格：Nasdaq、上交所／深交所、<br/>Yahoo（已標示）、你的 CSV",
          "📑 財報：Apple PDF、<br/>SEC 資料、你匯入的文件", "🖨 render_table<br/>render_chart", "🖨 quarterly_earnings", "🖼 PNG + HTML<br/>EN · 繁體中文"],
    h_install="安裝",
    install_intro="支援 macOS、Linux 與 Windows。需要 Python 3.9 以上（用於渲染），git 可有可無。安裝程式會一併註冊兩個 skill。",
    tip="💡 **最省事的辦法：** 把下面的提示詞直接貼給你的 AI Agent，它會替你裝好。",
    h_agent="🤖 讓 AI Agent 幫你安裝",
    agent_intro="把下面這段話貼給 Claude Code、Codex 或其他程式 Agent：",
    h_self="💻 或自己執行",
    install_note=("安裝程式會把主 skill 放進 `~/.claude/skills/schwab-performance-table`（Windows 為 `%USERPROFILE%\\.claude\\skills\\...`），"
                  "在裡面建立獨立的 Python 虛擬環境，安裝相依套件與 Chromium（約 100 MB），在旁邊註冊 `quarterly-earnings-review`，"
                  "再渲染所有表格版式、一張圖和一份財報表作為冒煙測試。一切正常時會輸出 `Render OK`。裝完請重新啟動 Claude，skill 才會載入。"
                  "想先看腳本內容，可以打開 [install.sh](install.sh) 或 [install.ps1](install.ps1)。"),
    opt_head=["選項（macOS / Linux）", "選項（Windows）", "作用"],
    opts=["裝到別處（例如其他 Agent 的 skills 目錄）。環境變數 `CLAUDE_SKILLS_DIR` 可修改預設根目錄。",
          "安裝指定的標籤或分支而不是 `main`，例如 `v0.6.1`，用來固定版本。不帶它再執行一次就會回到 `main`。",
          "略過 Python、Playwright 與 Chromium（只下載並註冊檔案）。",
          "刪除已安裝的 skill 資料夾，以及由它註冊的財報 skill。"],
    pipe_note="用管線執行時，選項要放在 `sh -s --` 後面，例如 `curl -fsSL .../install.sh | sh -s -- --dir ~/my-skills/schwab`。Windows 請先儲存 `install.ps1`，再執行 `.\\install.ps1 -Dir C:\\path`。",
    update_note="**更新：** 再執行一次同樣的命令。**解除安裝：** 加上 `--uninstall` 執行（Windows 用 `-Uninstall`）。",
    trouble="**常見問題：** Debian/Ubuntu 需要先裝 `python3-venv`。Linux 上 Chromium 無法啟動時，執行 `sudo <安裝目錄>/.venv/bin/python -m playwright install-deps chromium`。精簡的 Linux 伺服器請先裝一套 CJK 字型（`sudo apt install fonts-noto-cjk`），否則中文會顯示成方塊。",
    h_using="在 Claude 裡使用",
    using_intro="安裝後直接用自然語言說就行，例如：",
    using=["幫我給 NVDA、AMD、MU 做個業績表。",
           "把這張持倉截圖做成 Schwab 風格的表。（附上截圖）",
           "畫 NVDA、MU、AAPL 今年的走勢圖，並和標普 500 對比。",
           "把這六檔股票 3 月到 6 月的走勢用對數刻度對比一下。",
           "把 AAPL、MSFT、NVDA 做成摩根士丹利風格的回報與風險矩陣。",
           "畫 7203.T、0700.HK、600519.SS 今年以來的走勢。",
           "用 HSBC 表幫我看看 AAPL FY2025Q3 的財報。"],
    h_styles="表格版式",
    styles_intro="四種版式，用 `--style`（或 `spec.style`）選擇，預設是 Schwab。它們是獨立的範本，並非所列機構發布或與其有關的報告。",
    style_head=["版式", "呈現內容", "示例"],
    style_rows=[("Schwab · 排名表", "年初至今，加上在標普 500 與納斯達克內的排名（模式 A）"), ("Schwab · 持倉表", "開倉盈虧 %、當日盈虧、平均成本、持股數，來自截圖或匯出檔（模式 B）"),
                ("Schwab · 自選股表", "只給代碼：年初至今、近 1 月、近 1 年、最新收盤價（模式 C）"), ("摩根士丹利", "兩個期間 × 回報、波動率與回撤"),
                ("黑石", "行業或策略分組，兩個回報期間"), ("IBKR", "券商欄位、市值、權重與明確提供的敞口")],
    style_cmds=["# Schwab（預設）", "# 或 --style morgan | blackstone | ibkr", "# 用抓下來的價格產生矩陣"],
    style_note=("每個範本都有明確的欄位結構；把五欄的自選股表丟給七欄或九欄的版式，不會憑空補出缺少的資料。"
                "Schwab 表格與圖表保留淺色／深色模式，其他範本以白紙為準校準。欄位結構、來源樣本與字型替代說明見[範本指南](references/institutional-tables.md)。"),
    h_charts="走勢圖",
    charts_intro="最多 9 檔、任意時間段（預設年初至今），附回撤面板與彙總表。",
    layout_head=["版式", "內容", "適用"],
    layout_rows=[("`lines`", "折線圖、回撤面板、彙總表", "2–5 檔"), ("`multiples`", "每檔一個小圖，共用縱軸，下方帶回撤條", "6–9 檔")],
    layout_auto="`layout: auto` 會依標的數量自動選擇。",
    route_head=["標的", "來源", "說明"],
    route_rows=[("美股、ETF、納斯達克指數（`NVDA`、`BRK.B`、`SPY`、`COMP`）", "Nasdaq 官方收盤價", "已按拆股調整的價格回報，約 10 年歷史"),
                ("上海／深圳（`600519.SS`、`000001.SZ`）", "交易所網站", "未復權收盤價；深圳歷史長度有限"),
                ("其他交易所與指數（`7203.T`、`0700.HK`、`SAP.DE`、`^N225`）", "Yahoo Finance", "明確標示為聚合資料；請帶上交易所後綴"),
                ("你自己的檔案", "`csv_to_prices.py`", "任何市場；含復權收盤價的 CSV 可畫出標示清楚的總回報圖")],
    chart_bullets=["**基準：** 預設 SPY（標示為標普 500 的替代），最多兩個基準（`--benchmark SPY,COMP`），或用 `--benchmark none` 不畫基準。",
                   "**縱軸：** 只有一個縱軸，起點為 100。範圍很大時自動改用對數刻度（也可用 `y_scale` 指定）。",
                   "**選項：** `--theme dark`、`--pdf`、自訂線條顏色，HTML 檔裡還有滑鼠懸停提示。"],
    h_earn="季度財報解讀",
    earn_intro="直接說「用 HSBC 表幫我看看 AAPL FY2025Q3 的財報」。**quarterly-earnings-review** 會核對財季日期與原始財報，算出單季、同比與環比數字，並附上引用來源的解讀。輸出為繁體中文與英文的 PNG + HTML，另附原始事實與核對帳本。",
    earn_points=["**來源：** Apple 官方財務 PDF（FY2025Q3、FY2025Q4 已用真實原件驗證）；其他美國 GAAP 公司用 SEC Company Facts（解析器有固定測資覆蓋，即時存取可能被拒）；其他市場用 `--facts` 匯入已核實的官方財報。",
                 "**用公司財季，不是自然季：** 表上寫明實際的起訖日期。全年或累計數字不會被改標成單季事實；缺資料維持 NA。",
                 "**解讀：** 每則評論都引用來源帳本的 ID。沒有一致預期證據就不說超出／低於預期；分析文字不會覆蓋原始事實。"],
    earn_links="[線上兩季示範](https://imoneys10k.github.io/schwab-table/earnings/) · [用法與來源涵蓋範圍](EARNINGS.md) · [Skill](skills/quarterly-earnings-review/SKILL.md)",
    h_rules="資料與誠實原則",
    rules=["**來源一定印在腳註**，連同截止日與取得日。取不到的歷史會明說，不會悄悄縮短。",
           "**`null` 不是 0。** 缺資料顯示 `NA`；不憑記憶補、不猜。",
           "**自動來源只提供價格回報。** Nasdaq 的股息金額沒有按拆股調整，ETF 也沒有股息，所以總回報需要你自己提供復權收盤價 CSV。",
           "**Yahoo 一律標示為聚合資料**，不冒充交易所公布的收盤價。A 股網站價格未復權，工具會提醒公司行動造成的失真。",
           "**港股與其他市場要帶交易所後綴**（`0700.HK`）；單純的數字代碼有歧義，會被拒絕。",
           "給 Agent 看的細節在 [SKILL.md](SKILL.md)（繁體中文）與 [SKILL.en.md](SKILL.en.md)（英文）。"],
    sum_files="📁 檔案",
    files=[("`SKILL.md`、`SKILL.en.md`", "Claude 實際載入的 skill（繁體中文）與它的英文譯本"),
           ("`skills/quarterly-earnings-review/`", "財報 skill，由安裝程式註冊在主 skill 旁邊"),
           ("`install.sh`、`install.ps1`、`install_earnings_skill.py`", "macOS / Linux 與 Windows 的一鍵安裝程式，以及財報 skill 的註冊"),
           ("`render_table.py`、`institutional_tables.py`、`prices_to_table.py`", "表格渲染器與四種版式；用抓下來的價格產生摩根士丹利／黑石規格"),
           ("`fetch_prices.py`、`csv_to_prices.py`", "取得 Nasdaq、上海／深圳與 Yahoo 的日收盤價；轉換你自己的 CSV"),
           ("`render_chart.py`、`render_common.py`", "走勢圖渲染器；共用的主題與 PNG / PDF 輸出"),
           ("`quarterly_earnings.py`、`earnings_core.py`、`earnings_sources.py`、`render_earnings.py`", "財報指令、可核對的計算、來源轉接器與 HSBC 版式渲染器"),
           ("`localization.py`、`fonts.py`、`fonts/`", "繁體中文轉換；嵌入 HTML 的隨附字型（含授權）"),
           ("`references/`、`EARNINGS.md`", "範本指南；財報用法與來源涵蓋範圍（繁體中文）"),
           ("`examples/`、`docs/`", "規格與渲染範例（`sample_prices.json` 為合成資料）；GitHub Pages 網站"),
           ("`tests/`、`evals/`", "單元測試；貼近真實使用的 Agent 請求、觸發測試集與結果"),
           ("`tools/build_docs.py`", "由同一份內容表產生這些 README 與網站"),
           ("`requirements.txt`、`CHANGELOG.md`、`CONTRIBUTING.md`、`assets/`", "相依套件、更新紀錄、貢獻規則、橫幅與社群卡片")],
    sum_manual="🔧 手動渲染",
    manual_intro="用安裝程式裝的話，腳本會自動切換到專屬虛擬環境，直接 `python3 render_table.py ...` 就行。否則需要 Python 3.9 以上：",
    manual_after=("兩個渲染器通用的選項：`--langs en` 只渲染指定語言（逗號分隔，`zh` 是繁體中文，`_zh` 檔名照舊）、"
                  "`--no-png` 只寫 HTML 不需要瀏覽器、`--scale 3` 提高 PNG 清晰度（預設 2，即 1520 px 寬）、`--theme dark`、`--pdf`。輸出資料夾不存在時會自動建立。"),
    manual_fetch=("`fetch_prices.py` 最多快取 12 小時（`--refresh` 可繞過），而且只有在快取已包含最新應有收盤價時才重用；網路失敗時會帶警告地使用上一次的快取。"
                  "代碼有歧義時，可用 `index:COMP`、`etf:SPY` 指定資產類別。走勢圖分兩步：先抓價格再渲染，用 `--start` / `--end` 指定期間。"),
    manual_fonts=("字型：隨附並嵌入 Inter、Source Sans 3 與 Droid Sans 用於拉丁字母；中文使用系統的繁體中文字型。與原稿字型的替代差異見[範本指南](references/institutional-tables.md)。不散布參考 PDF 或 macOS 的專有字型。"),
    h_test="測試與評測",
    test_text=("`python3 -m unittest discover -s tests -v` 會跑回報、回撤、波動率、代碼路由、快取新鮮度、CSV 匯入、表格版式與財報計算的標準答案測試。"
               "CI 在 Ubuntu、macOS、Windows（Python 3.9 與 3.13）上執行這些測試，重新產生範例並檢查沒有變動，執行即時的 Nasdaq 冒煙測試，並在三個系統上安裝 skill。"
               "[evals/](evals/README.md) 收錄貼近真實使用的 Agent 請求與第一輪結果。README 與網站由 `python3 tools/build_docs.py` 產生，內容過期時測試會失敗。"),
    h_disc="免責聲明",
    disc="本專案只負責整理資料的呈現，不提供任何投資建議。除圖庫說明另有註明外，示例使用虛構公司與合成數值。報表版式是獨立範本，並非所列機構發布的報告。",
    h_lic="授權",
    star="⭐ 如果它幫你省了時間，點個 star 能讓更多人看到。",
    hero_a="研報風格的表格、", hero_b="走勢圖與財報解讀。",
    site_sub="機構版式的表格與走勢圖，加上用原始財報做出的 HSBC 版式季度財報解讀。繁體中文與英文，PNG + HTML。",
    cta1="一行指令安裝", cta2="在 GitHub 查看", cta3="財報示範",
    t_modes="選個版式",
    t_earn="從財報原件出發的季度解讀",
    earn_btn="打開示範", t_data="數字從哪裡來",
    tab_unix="macOS / Linux", tab_win="Windows", or_agent="或讓 AI Agent 替你裝", copy="複製", copied="已複製",
    docs_label="文件", foot="MIT 授權。僅作示範，不構成投資建議。",
)

# =====================================================================================================================
C["ja"] = dict(
    tagline="AI エージェントのための、リサーチ風の表・推移チャート・四半期決算レビュー。",
    links=["🚀 インストール", "🎨 ギャラリー", "🌐 プロジェクトサイト", "🧾 決算デモ", "📘 Skill ドキュメント"],
    intro=("1 つのリポジトリに Claude スキルが 2 つあります。**schwab-performance-table** は、銘柄リスト、証券口座の保有銘柄スクリーンショット、価格データ、自分の CSV を、"
           "リサーチ風の表（Schwab・Morgan・Blackstone・IBKR レイアウト）に、またドローダウンと対数目盛つきの推移チャートに変換します。"
           "**quarterly-earnings-review** は企業の四半期決算の原本を確認し、出典付きの解説を添えた HSBC 風の決算表を作ります。"
           "出力はすべて英語と繁体字中国語の 2 版で、PNG と単体で完結する HTML です。"),
    h_high="特長",
    cards=[
        ("🎯", "4 つのレポートレイアウト", "Schwab、Morgan、Blackstone、IBKR 風。列の構成は明示されています。独立したテンプレートで、各機関が発行したレポートではありません。"),
        ("📊", "表・チャート・決算", "ランキング表・保有銘柄表・ウォッチリスト表、ドローダウンと対数目盛つきの折れ線とスモールマルチプル、HSBC 風の四半期決算。"),
        ("🌏", "英語と繁体字中国語", "出力は常に 2 言語。2x PNG と単体で完結する HTML に加え、ダークテーマと PDF も選べます。"),
        ("🔒", "出典を必ず明示", "Nasdaq と上海・深圳取引所の終値、出典を明示した Yahoo のデータ（その他の市場）、決算は SEC と Apple の公式資料。欠損は NA で、作り話はしません。"),
        ("🤖", "ワンフレーズで導入", "プロンプトを Claude Code や Codex に貼るだけ。macOS・Linux・Windows に対応し、2 つのスキルを一緒に入れます。"),
        ("🧪", "テスト済み", "正解つきの単体テスト、3 つの OS での CI、実データのスモークテスト、最初のエージェント評価。"),
    ],
    h_gallery="ギャラリー",
    gallery=[("ランキング表", "EN"), ("ウォッチリスト表", "繁體中文"), ("ドローダウン付き折れ線", "EN"), ("スモールマルチプル（対数目盛）", "繁體中文"),
             ("Morgan 風マトリクス", "繁體中文"), ("Blackstone 風の成績表", "繁體中文"), ("IBKR 風の保有明細", "繁體中文"),
             ("HSBC 風の四半期決算：AAPL 第 3 四半期", "繁體中文"), ("HSBC 風の四半期決算：AAPL 第 4 四半期", "繁體中文"), ("保有銘柄表", "EN")],
    gallery_note="決算の例は Apple の公式資料、ランキング表は Charles Schwab の公開チャートを使用しています。それ以外は架空の企業と合成データです。",
    h_flow="仕組み",
    flow=["📝 ティッカー、画像、CSV<br/>またはティッカー＋四半期", "🤖 Claude + スキル", "🏛 価格：Nasdaq、上海・深圳、<br/>Yahoo（明示）、自分の CSV",
          "📑 決算：Apple の PDF、<br/>SEC のデータ、取り込んだ資料", "🖨 render_table<br/>render_chart", "🖨 quarterly_earnings", "🖼 PNG + HTML<br/>EN · 繁體中文"],
    h_install="インストール",
    install_intro="macOS、Linux、Windows に対応しています。Python 3.9 以上（描画用）が必要で、git は任意です。インストーラーは 2 つのスキルをまとめて登録します。",
    tip="💡 **いちばん簡単な方法：** 下のプロンプトを AI エージェントに貼れば、すべてインストールしてくれます。",
    h_agent="🤖 AI エージェントにインストールしてもらう",
    agent_intro="次の文章を Claude Code、Codex などのコーディングエージェントにそのまま送ってください。",
    h_self="💻 自分で実行する",
    install_note=("インストーラーはメインのスキルを `~/.claude/skills/schwab-performance-table`（Windows では `%USERPROFILE%\\.claude\\skills\\...`）に置き、"
                  "その中に専用の Python 仮想環境を作って依存パッケージと Chromium（約 100 MB）を入れ、隣に `quarterly-earnings-review` を登録し、"
                  "すべての表スタイル・チャート 1 枚・決算表 1 枚をレンダリングして動作確認します。すべて正常なら `Render OK` と表示されます。"
                  "完了後に Claude を再起動すると、スキルが読み込まれます。実行前に内容を確認したい場合は [install.sh](install.sh) または [install.ps1](install.ps1) を開いてください。"),
    opt_head=["オプション（macOS / Linux）", "オプション（Windows）", "内容"],
    opts=["別の場所にインストール（他のエージェントの skills フォルダなど）。環境変数 `CLAUDE_SKILLS_DIR` で既定のルートを変更できます。",
          "`main` の代わりにタグまたはブランチをインストール（例：`v0.6.1`）。バージョン固定に使います。付けずにもう一度実行すると `main` に戻ります。",
          "Python・Playwright・Chromium をスキップ（ファイルの取得と登録のみ）。",
          "インストール済みのスキルフォルダと、それが登録した決算スキルを削除します。"],
    pipe_note="パイプで実行する場合、オプションは `sh -s --` の後ろに付けます。例：`curl -fsSL .../install.sh | sh -s -- --dir ~/my-skills/schwab`。Windows では `install.ps1` を保存してから `.\\install.ps1 -Dir C:\\path` を実行してください。",
    update_note="**更新：** 同じコマンドをもう一度実行します。**アンインストール：** `--uninstall` を付けて実行します（Windows は `-Uninstall`）。",
    trouble="**トラブルシューティング：** Debian/Ubuntu では先に `python3-venv` をインストールしてください。Linux で Chromium が起動しない場合は `sudo <インストール先>/.venv/bin/python -m playwright install-deps chromium` を実行してください。最小構成の Linux サーバーでは CJK フォント（`sudo apt install fonts-noto-cjk`）も入れてください。ないと中国語が四角で表示されます。",
    h_using="Claude での使い方",
    using_intro="インストール後は、普通の言葉で頼むだけです。例：",
    using=["NVDA、AMD、MU のパフォーマンス表を作って。",
           "この保有銘柄のスクリーンショットを Schwab 風の表にして。（スクリーンショットを添付）",
           "NVDA、MU、AAPL の今年の推移を S&P 500 と比べてチャートにして。",
           "この 6 銘柄の 3 月から 6 月の推移を対数目盛で比較して。",
           "AAPL、MSFT、NVDA を Morgan 風のリターンとリスクのマトリクスにして。",
           "7203.T、0700.HK、600519.SS の年初来の推移をチャートにして。",
           "AAPL の FY2025Q3 決算を HSBC 風の表でレビューして。"],
    h_styles="表のスタイル",
    styles_intro="4 つのレイアウトを `--style`（または `spec.style`。既定は Schwab）で選びます。独立したテンプレートで、記載の機関が発行した、あるいは関係するレポートではありません。",
    style_head=["スタイル", "内容", "サンプル"],
    style_rows=[("Schwab · ランキング", "YTD と S&P 500・NASDAQ 内での順位（モード A）"), ("Schwab · 保有銘柄", "建玉損益 %、当日損益、平均取得単価、保有株数。スクリーンショットやエクスポートから（モード B）"),
                ("Schwab · ウォッチリスト", "ティッカーだけで：年初来、直近 1 か月、直近 1 年、最新終値（モード C）"), ("Morgan", "2 期間 × リターン、変動率、ドローダウン"),
                ("Blackstone", "業種・戦略別のグループと 2 期間のリターン"), ("IBKR", "証券口座の項目、時価、比率、明示されたエクスポージャー")],
    style_cmds=["# Schwab（既定）", "# または --style morgan | blackstone | ibkr", "# 取得した価格からマトリクスを作る"],
    style_note=("各テンプレートは列の構成が明示されています。5 列のウォッチリストを 7 列や 9 列のレイアウトに渡しても、足りない項目を作り出すことはありません。"
                "Schwab の表とチャートはライト／ダークの両方に対応し、他のテンプレートは白い紙を基準に調整してあります。列構成、出典サンプル、フォント代替は[テンプレートガイド](references/institutional-tables.md)を参照してください。"),
    h_charts="推移チャート",
    charts_intro="最大 9 銘柄を任意の期間（既定は年初来）でチャート化します。ドローダウンのパネルとサマリー表が付きます。",
    layout_head=["レイアウト", "内容", "向いているケース"],
    layout_rows=[("`lines`", "折れ線チャート、ドローダウンパネル、サマリー表", "2〜5 銘柄"), ("`multiples`", "銘柄ごとの小さなチャート（共通スケール）と、その下のドローダウン帯", "6〜9 銘柄")],
    layout_auto="`layout: auto` は銘柄数に応じて自動で選びます。",
    route_head=["銘柄", "出典", "備考"],
    route_rows=[("米国株、ETF、Nasdaq の指数（`NVDA`、`BRK.B`、`SPY`、`COMP`）", "Nasdaq 公式終値", "株式分割調整済みの価格リターン、約 10 年分"),
                ("上海・深圳（`600519.SS`、`000001.SZ`）", "取引所のウェブサイト", "調整なしの終値。深圳は履歴が限られます"),
                ("その他の取引所と指数（`7203.T`、`0700.HK`、`SAP.DE`、`^N225`）", "Yahoo Finance", "集約データであることを明記。取引所サフィックスを付けてください"),
                ("自分のファイル", "`csv_to_prices.py`", "どの市場でも可。調整後終値の CSV なら総リターンのチャートを明示つきで描けます")],
    chart_bullets=["**ベンチマーク：** 既定は SPY（S&P 500 の代用と明記）。最大 2 つまで（`--benchmark SPY,COMP`）、`--benchmark none` で非表示。",
                   "**軸：** Y 軸は 1 本だけで、開始時点を 100 に指数化します。値幅が大きいときは自動で対数目盛に切り替わります（`y_scale` で指定も可能）。",
                   "**オプション：** `--theme dark`、`--pdf`、線の色の指定、HTML でのマウスオーバー表示。"],
    h_earn="四半期決算レビュー",
    earn_intro="「AAPL の FY2025Q3 決算を HSBC 風の表でレビューして」と頼むだけです。**quarterly-earnings-review** は会計期間と決算の原本を確認し、単四半期・前年同期比・前四半期比の数値を計算して、出典を引用した解説を添えます。出力は英語と繁体字中国語の PNG + HTML に、元データと検証台帳が付きます。",
    earn_points=["**出典：** Apple の公式決算 PDF（FY2025Q3・FY2025Q4 は実物で検証済み）。その他の米国 GAAP 企業は SEC Company Facts（パーサーは固定フィクスチャで検証済み、実アクセスは拒否されることがあります）。他の市場は `--facts` で取り込んだ検証済みの公式資料。",
                 "**暦ではなく会計四半期：** 表には実際の期間の開始日と終了日を書きます。年間・累計の数値を四半期の事実として付け替えることはなく、欠損は NA のままです。",
                 "**解説：** すべてのコメントは出典台帳の ID を引用します。コンセンサスの根拠がなければ上回った・下回ったとは言わず、分析文が元の事実を上書きすることもありません。"],
    earn_links="[2 四半期のオンラインデモ](https://imoneys10k.github.io/schwab-table/earnings/) · [使い方と出典の範囲](EARNINGS.md)（繁体字中国語） · [Skill](skills/quarterly-earnings-review/SKILL.md)",
    h_rules="データと誠実さのルール",
    rules=["**出典は必ず注記に印字**します。基準日と取得日も付けます。取得できなかった履歴は明示し、黙って短くはしません。",
           "**`null` は 0 ではありません。** 欠損は `NA` と表示し、記憶で埋めたり推測したりしません。",
           "**自動取得は価格リターンのみ。** Nasdaq の配当額は株式分割調整がされておらず、ETF には配当データがないため、総リターンには自分で用意した調整後終値の CSV が必要です。",
           "**Yahoo は集約データと明記**し、取引所が公表した終値とは扱いません。A 株のウェブサイト価格は調整なしで、コーポレートアクションによる歪みを警告します。",
           "**香港などの市場は取引所サフィックスが必要**です（`0700.HK`）。数字だけのコードは曖昧なので拒否されます。",
           "エージェント向けの詳細は [SKILL.md](SKILL.md)（繁体字中国語）と [SKILL.en.md](SKILL.en.md)（英語）にあります。"],
    sum_files="📁 ファイル",
    files=[("`SKILL.md`、`SKILL.en.md`", "Claude が読み込むスキル（繁体字中国語）とその英語訳"),
           ("`skills/quarterly-earnings-review/`", "決算スキル。インストーラーがメインのスキルの隣に登録します"),
           ("`install.sh`、`install.ps1`、`install_earnings_skill.py`", "macOS / Linux と Windows 用のワンクリックインストーラーと、決算スキルの登録"),
           ("`render_table.py`、`institutional_tables.py`、`prices_to_table.py`", "表のレンダラーと 4 つのスタイル。取得した価格から Morgan / Blackstone の spec を作成"),
           ("`fetch_prices.py`、`csv_to_prices.py`", "Nasdaq・上海/深圳・Yahoo の日次終値の取得、自分の CSV の変換"),
           ("`render_chart.py`、`render_common.py`", "チャートのレンダラー。共通のテーマと PNG / PDF の出力"),
           ("`quarterly_earnings.py`、`earnings_core.py`、`earnings_sources.py`、`render_earnings.py`", "決算コマンド、検証可能な計算、出典アダプター、HSBC 風レンダラー"),
           ("`localization.py`、`fonts.py`、`fonts/`", "繁体字中国語への変換。HTML に埋め込む同梱フォント（ライセンス付き）"),
           ("`references/`、`EARNINGS.md`", "テンプレートガイド。決算の使い方と出典の範囲（繁体字中国語）"),
           ("`examples/`、`docs/`", "spec とレンダリング済みの例（`sample_prices.json` は合成データ）。GitHub Pages のサイト"),
           ("`tests/`、`evals/`", "単体テスト。実際の使い方に近いエージェント依頼、トリガーテストのセット、結果"),
           ("`tools/build_docs.py`", "1 つの内容表からこれらの README とサイトを生成"),
           ("`requirements.txt`、`CHANGELOG.md`、`CONTRIBUTING.md`、`assets/`", "依存パッケージ、変更履歴、貢献ルール、バナーとソーシャルカード")],
    sum_manual="🔧 手動レンダリング",
    manual_intro="インストーラーを使った場合、スクリプトは自動で専用の仮想環境に切り替わるので、そのまま `python3 render_table.py ...` で動きます。そうでない場合は Python 3.9 以上が必要です。",
    manual_after=("両方のレンダラー共通のオプション：`--langs en` は指定した言語のみレンダリング（カンマ区切り。`zh` は繁体字中国語で、`_zh` のファイル名は従来どおり）、"
                  "`--no-png` は HTML のみでブラウザ不要、`--scale 3` で PNG の解像度を上げます（既定は 2、幅 1520 px）、`--theme dark`、`--pdf`。出力先フォルダがなければ自動で作成されます。"),
    manual_fetch=("`fetch_prices.py` は応答を最大 12 時間キャッシュし（`--refresh` で無視）、最新の終値をすでに含んでいる場合だけキャッシュを再利用します。ネットワークに失敗した場合は、警告つきで直前のキャッシュを使います。"
                  "コードが曖昧なときは `index:COMP`、`etf:SPY` で資産クラスを指定できます。チャートは価格を取得してから描画する 2 ステップで、期間は `--start` / `--end` で指定します。"),
    manual_fonts=("フォント：Inter、Source Sans 3、Droid Sans を同梱して英数字用に埋め込みます。中国語はシステムの繁体字フォントを使います。原本とのフォント代替は[テンプレートガイド](references/institutional-tables.md)を参照してください。参照 PDF や macOS の専有フォントは配布しません。"),
    h_test="テストと評価",
    test_text=("`python3 -m unittest discover -s tests -v` は、リターン・ドローダウン・変動率・銘柄ルーティング・キャッシュの鮮度・CSV 取り込み・表スタイル・決算計算の正解つきテストを実行します。"
               "CI は Ubuntu・macOS・Windows（Python 3.9 と 3.13）でこれらを実行し、例を再生成して変化がないか確認し、Nasdaq への実データのスモークテストを行い、3 つの OS でスキルをインストールします。"
               "[evals/](evals/README.md) には実際の使い方に近いエージェント依頼と最初の結果があります。README とサイトは `python3 tools/build_docs.py` で生成され、内容が古いとテストが失敗します。"),
    h_disc="免責事項",
    disc="このプロジェクトはデータの見せ方を整えるだけで、投資助言は行いません。ギャラリーの注記に別の記載がない限り、例は架空の企業と合成値です。レポートのレイアウトは独立したテンプレートで、記載の機関が発行したレポートではありません。",
    h_lic="ライセンス",
    star="⭐ 役に立ったら、スターをもらえると他の人にも見つけてもらえます。",
    hero_a="リサーチ風の表、", hero_b="チャート、決算レビュー。",
    site_sub="機関投資家風の表と推移チャート、さらに原本をもとにした HSBC 風の四半期決算レビュー。英語と繁体字中国語、PNG + HTML。",
    cta1="1 行でインストール", cta2="GitHub で見る", cta3="決算デモ",
    t_modes="レイアウトを選ぶ",
    t_earn="原本から作る四半期決算",
    earn_btn="デモを開く", t_data="数字の出どころ",
    tab_unix="macOS / Linux", tab_win="Windows", or_agent="または AI エージェントにおまかせ", copy="コピー", copied="コピーしました",
    docs_label="ドキュメント", foot="MIT ライセンス。例示のみで、投資助言ではありません。",
)

# =====================================================================================================================
C["fr"] = dict(
    tagline="Tableaux façon étude, graphiques de cours et analyses de résultats trimestriels pour votre agent IA.",
    links=["🚀 Installation", "🎨 Galerie", "🌐 Site du projet", "🧾 Démo résultats", "📘 Doc du skill"],
    intro=("Deux skills Claude dans un seul dépôt. **schwab-performance-table** transforme une liste d'actions, une capture de positions chez un courtier, des données de prix ou vos propres "
           "fichiers CSV en tableaux façon étude (dispositions Schwab, Morgan, Blackstone et IBKR) et en graphiques de cours avec drawdown et échelle logarithmique. "
           "**quarterly-earnings-review** vérifie le document trimestriel d'une société et produit un tableau de résultats de style HSBC avec des commentaires sourcés. "
           "Tout est produit en anglais et en chinois traditionnel, en PNG et en HTML autonome."),
    h_high="Points forts",
    cards=[
        ("🎯", "Quatre dispositions de rapport", "Styles Schwab, Morgan, Blackstone et IBKR, avec des schémas de colonnes explicites. Ce sont des modèles indépendants, pas des rapports publiés par ces institutions."),
        ("📊", "Tableaux, graphiques, résultats", "Tableaux de classement, de positions et de liste de suivi ; courbes et petits multiples avec drawdown et échelle logarithmique ; résultats trimestriels de style HSBC."),
        ("🌏", "Anglais et chinois traditionnel", "Chaque sortie existe dans les deux langues : PNG en 2x et HTML autonome, avec thème sombre et PDF en option."),
        ("🔒", "Sources toujours indiquées", "Cours des bourses Nasdaq et Shanghai/Shenzhen, données Yahoo clairement identifiées pour les autres marchés, documents SEC et Apple pour les résultats. Une donnée manquante est marquée NA, jamais inventée."),
        ("🤖", "Installation en une phrase", "Collez un message dans Claude Code ou Codex. Fonctionne sous macOS, Linux et Windows et installe les deux skills."),
        ("🧪", "Testé", "Tests unitaires à réponses connues, CI sur trois systèmes, test de fumée sur données réelles et première série d'évaluations d'agent."),
    ],
    h_gallery="Galerie",
    gallery=[("Tableau de classement", "EN"), ("Tableau de liste de suivi", "繁體中文"), ("Courbes avec drawdown", "EN"), ("Petits multiples, échelle log", "繁體中文"),
             ("Matrice façon Morgan", "繁體中文"), ("Performance façon Blackstone", "繁體中文"), ("Positions façon IBKR", "繁體中文"),
             ("Résultats HSBC, AAPL T3", "繁體中文"), ("Résultats HSBC, AAPL T4", "繁體中文"), ("Tableau de positions", "EN")],
    gallery_note="Les exemples de résultats utilisent les publications officielles d'Apple et le tableau de classement un graphique public de Charles Schwab. Tout le reste utilise des sociétés fictives et des données synthétiques.",
    h_flow="Fonctionnement",
    flow=["📝 Symboles, capture, CSV<br/>ou symbole + trimestre", "🤖 Claude + skills", "🏛 Prix : Nasdaq, SSE/SZSE,<br/>Yahoo (indiqué), votre CSV",
          "📑 Documents : PDF Apple,<br/>données SEC, vos imports", "🖨 render_table<br/>render_chart", "🖨 quarterly_earnings", "🖼 PNG + HTML<br/>EN · 繁體中文"],
    h_install="Installation",
    install_intro="Fonctionne sous macOS, Linux et Windows. Python 3.9 ou supérieur est nécessaire (pour produire les rendus) ; git est facultatif. L'installateur enregistre les deux skills.",
    tip="💡 **Le plus simple :** collez le message ci-dessous dans votre agent IA, il installe tout pour vous.",
    h_agent="🤖 Laissez votre agent IA l'installer",
    agent_intro="Collez ce message dans Claude Code, Codex ou tout autre agent de programmation :",
    h_self="💻 Ou lancez-le vous-même",
    install_note=("L'installateur place le skill principal dans `~/.claude/skills/schwab-performance-table` (`%USERPROFILE%\\.claude\\skills\\...` sous Windows), "
                  "crée un environnement virtuel Python dédié à l'intérieur, installe les dépendances et Chromium (environ 100 Mo), enregistre "
                  "`quarterly-earnings-review` à côté, puis génère tous les styles de tableau, un graphique et un tableau de résultats comme test de fumée. "
                  "Il affiche `Render OK` quand tout fonctionne. Redémarrez ensuite Claude pour que les skills soient pris en compte. "
                  "Pour lire un script avant de l'exécuter, ouvrez [install.sh](install.sh) ou [install.ps1](install.ps1)."),
    opt_head=["Option (macOS / Linux)", "Option (Windows)", "Effet"],
    opts=["Installer ailleurs (par exemple dans le dossier skills d'un autre agent). La variable `CLAUDE_SKILLS_DIR` change la racine par défaut.",
          "Installer un tag ou une branche au lieu de `main`, par exemple `v0.6.1`, pour figer une version. Relancez sans cette option pour revenir à `main`.",
          "Ignorer Python, Playwright et Chromium (récupérer et enregistrer seulement les fichiers).",
          "Supprimer le dossier du skill installé et le skill de résultats qu'il a enregistré."],
    pipe_note="Avec un tube (pipe), passez les options après `sh -s --`, par exemple `curl -fsSL .../install.sh | sh -s -- --dir ~/my-skills/schwab`. Sous Windows, enregistrez `install.ps1` puis lancez `.\\install.ps1 -Dir C:\\path`.",
    update_note="**Mise à jour :** relancez la même commande. **Désinstallation :** lancez-la avec `--uninstall` (`-Uninstall` sous Windows).",
    trouble="**Dépannage :** sous Debian/Ubuntu, installez d'abord `python3-venv`. Sous Linux, si Chromium ne démarre pas, exécutez `sudo <dossier d'installation>/.venv/bin/python -m playwright install-deps chromium`. Sur un serveur Linux minimal, installez aussi une police CJK (`sudo apt install fonts-noto-cjk`), sinon le chinois s'affiche en carrés.",
    h_using="Utilisation avec Claude",
    using_intro="Une fois installé, il suffit de demander en langage naturel, par exemple :",
    using=["Fais-moi un tableau de performance pour NVDA, AMD et MU.",
           "Transforme cette capture d'écran de positions en tableau de style Schwab. (joindre la capture)",
           "Trace NVDA, MU et AAPL depuis le début de l'année face au S&P 500.",
           "Compare ces six actions de mars à juin en échelle logarithmique.",
           "Présente AAPL, MSFT et NVDA dans une matrice rendement/risque façon Morgan.",
           "Trace 7203.T, 0700.HK et 600519.SS depuis le début de l'année.",
           "Analyse les résultats AAPL FY2025Q3 dans un tableau de style HSBC."],
    h_styles="Styles de tableau",
    styles_intro="Quatre dispositions, choisies avec `--style` (ou `spec.style` ; Schwab par défaut). Ce sont des modèles indépendants, pas des rapports publiés par les institutions citées ni liés à elles.",
    style_head=["Style", "Contenu", "Exemple"],
    style_rows=[("Schwab · classement", "YTD et rang dans le S&P 500 et le NASDAQ (mode A)"), ("Schwab · positions", "Gain/perte latent en %, gain/perte du jour, coût moyen, nombre de titres, à partir d'une capture ou d'un export (mode B)"),
                ("Schwab · liste de suivi", "Uniquement des symboles : YTD, 1 mois, 1 an, dernier cours (mode C)"), ("Morgan", "Deux périodes × rendement, volatilité et drawdown"),
                ("Blackstone", "Groupes par secteur ou stratégie, deux périodes de rendement"), ("IBKR", "Champs du courtier, valeurs de marché, poids et exposition fournie")],
    style_cmds=["# Schwab (par défaut)", "# ou --style morgan | blackstone | ibkr", "# construire une matrice à partir des prix récupérés"],
    style_note=("Chaque modèle a des schémas de colonnes explicites ; passer un tableau de suivi à cinq colonnes à une disposition de sept ou neuf colonnes n'invente pas les données manquantes. "
                "Les tableaux et graphiques Schwab gardent les modes clair et sombre ; les autres modèles sont calibrés pour du papier blanc. Schémas, échantillons de sources et substitutions de polices : voir le [guide des modèles](references/institutional-tables.md)."),
    h_charts="Graphiques de cours",
    charts_intro="Jusqu'à 9 valeurs sur une période au choix (par défaut : depuis le début de l'année), avec un panneau de drawdown et un tableau de synthèse.",
    layout_head=["Disposition", "Contenu", "Pour"],
    layout_rows=[("`lines`", "Courbes, panneau de drawdown, tableau de synthèse", "2 à 5 valeurs"), ("`multiples`", "Un petit graphique par valeur à échelle commune, avec une bande de drawdown dessous", "6 à 9 valeurs")],
    layout_auto="`layout: auto` choisit selon le nombre de valeurs.",
    route_head=["Symboles", "Source", "Remarques"],
    route_rows=[("Actions US, ETF, indices Nasdaq (`NVDA`, `BRK.B`, `SPY`, `COMP`)", "Cours de clôture officiels Nasdaq", "Rendement de prix ajusté des divisions de titres, environ 10 ans d'historique"),
                ("Shanghai / Shenzhen (`600519.SS`, `000001.SZ`)", "Sites des bourses", "Cours non ajustés ; l'historique de Shenzhen est limité"),
                ("Autres bourses et indices (`7203.T`, `0700.HK`, `SAP.DE`, `^N225`)", "Yahoo Finance", "Clairement indiqué comme donnée agrégée ; utilisez le suffixe de la bourse"),
                ("Vos propres fichiers", "`csv_to_prices.py`", "Tout marché ; un CSV de cours ajustés donne un graphique de rendement total clairement étiqueté")],
    chart_bullets=["**Référence :** SPY par défaut (indiqué comme substitut du S&P 500), jusqu'à deux références (`--benchmark SPY,COMP`), ou `--benchmark none`.",
                   "**Axe :** un seul axe vertical, indexé à 100 au départ. Il passe automatiquement en échelle logarithmique quand l'écart est grand (ou fixez `y_scale`).",
                   "**Options :** `--theme dark`, `--pdf`, couleurs de courbes personnalisées et infobulles au survol dans les fichiers HTML."],
    h_earn="Analyse des résultats trimestriels",
    earn_intro="Demandez « Analyse les résultats AAPL FY2025Q3 dans un tableau de style HSBC ». Le skill **quarterly-earnings-review** vérifie les dates de l'exercice et le document d'origine, calcule les valeurs du trimestre, en glissement annuel et par rapport au trimestre précédent, et ajoute des commentaires qui citent leurs sources. La sortie est un PNG + HTML en anglais et en chinois traditionnel, avec les faits bruts et un registre de vérification.",
    earn_points=["**Sources :** PDF financiers officiels d'Apple (vérifiés sur pièces pour FY2025Q3 et FY2025Q4) ; autres sociétés US-GAAP via SEC Company Facts (l'analyseur est couvert par des jeux de test fixes, l'accès en direct peut être refusé) ; autres marchés via des rapports officiels vérifiés importés avec `--facts`.",
                 "**Trimestres fiscaux, pas civils :** le tableau indique les vraies dates de la période. Un chiffre annuel ou cumulé n'est jamais présenté comme un fait trimestriel ; une donnée manquante reste NA.",
                 "**Commentaires :** chaque commentaire cite un identifiant du registre des sources. Aucune affirmation de dépassement ou de déception sans preuve du consensus ; l'analyse n'écrase jamais les faits."],
    earn_links="[Démo en ligne sur deux trimestres](https://imoneys10k.github.io/schwab-table/earnings/) · [Usage et couverture des sources](EARNINGS.md) (en chinois traditionnel) · [Skill](skills/quarterly-earnings-review/SKILL.md)",
    h_rules="Règles sur les données et l'honnêteté",
    rules=["**Les sources sont toujours imprimées** en note de bas de tableau, avec la date de référence et la date de récupération. Un historique indisponible est signalé, jamais raccourci en silence.",
           "**`null` n'est pas zéro.** Une donnée manquante s'affiche `NA` ; rien n'est complété de mémoire ni deviné.",
           "**Rendement de prix seulement pour les sources automatiques.** Les montants de dividendes de Nasdaq ne sont pas ajustés des divisions de titres et les ETF n'en ont pas ; le rendement total demande donc votre propre CSV de cours ajustés.",
           "**Yahoo est indiqué comme donnée agrégée**, pas comme cours publiés par la bourse. Les prix des sites des bourses chinoises ne sont pas ajustés ; les outils avertissent des distorsions dues aux opérations sur titres.",
           "**Hong Kong et les autres marchés demandent le suffixe de la bourse** (`0700.HK`) ; un code purement numérique est ambigu et refusé.",
           "Les détails pour les agents sont dans [SKILL.md](SKILL.md) (chinois traditionnel) et [SKILL.en.md](SKILL.en.md) (anglais)."],
    sum_files="📁 Fichiers",
    files=[("`SKILL.md`, `SKILL.en.md`", "Le skill chargé par Claude (chinois traditionnel) et sa traduction anglaise"),
           ("`skills/quarterly-earnings-review/`", "Le skill de résultats, enregistré à côté du skill principal par les installateurs"),
           ("`install.sh`, `install.ps1`, `install_earnings_skill.py`", "Installateurs en une commande pour macOS / Linux et Windows, et enregistrement du skill de résultats"),
           ("`render_table.py`, `institutional_tables.py`, `prices_to_table.py`", "Moteur de rendu des tableaux et ses quatre styles ; construit des spécifications Morgan / Blackstone à partir des prix"),
           ("`fetch_prices.py`, `csv_to_prices.py`", "Cours de clôture quotidiens de Nasdaq, Shanghai/Shenzhen et Yahoo ; conversion de vos fichiers CSV"),
           ("`render_chart.py`, `render_common.py`", "Moteur de rendu des graphiques ; thèmes et sorties PNG / PDF partagés"),
           ("`quarterly_earnings.py`, `earnings_core.py`, `earnings_sources.py`, `render_earnings.py`", "Commande de résultats, calculs vérifiables, adaptateurs de sources et rendu de style HSBC"),
           ("`localization.py`, `fonts.py`, `fonts/`", "Conversion en chinois traditionnel ; polices fournies et intégrées au HTML (licences incluses)"),
           ("`references/`, `EARNINGS.md`", "Guide des modèles ; usage et couverture des sources pour les résultats (chinois traditionnel)"),
           ("`examples/`, `docs/`", "Spécifications et rendus d'exemple (`sample_prices.json` est synthétique) ; le site GitHub Pages"),
           ("`tests/`, `evals/`", "Tests unitaires ; demandes d'agent réalistes, jeu de tests de déclenchement et résultats"),
           ("`tools/build_docs.py`", "Génère ces README et le site à partir d'une seule table de contenu"),
           ("`requirements.txt`, `CHANGELOG.md`, `CONTRIBUTING.md`, `assets/`", "Dépendances, historique, règles de contribution, bannière et carte sociale")],
    sum_manual="🔧 Rendu manuel",
    manual_intro="Si vous avez utilisé l'installateur, les scripts basculent automatiquement sur leur environnement virtuel : `python3 render_table.py ...` suffit. Sinon, Python 3.9 ou supérieur est requis :",
    manual_after=("Options des deux moteurs : `--langs en` ne rend que les langues indiquées (séparées par des virgules ; `zh` est le chinois traditionnel et les noms `_zh` sont conservés), "
                  "`--no-png` n'écrit que le HTML sans navigateur, `--scale 3` augmente la résolution des PNG (2 par défaut, soit 1520 px de large), `--theme dark` et `--pdf`. Les dossiers de sortie manquants sont créés."),
    manual_fetch=("`fetch_prices.py` met les réponses en cache jusqu'à 12 heures (`--refresh` l'ignore) et ne réutilise un cache que s'il contient déjà la dernière clôture attendue. "
                  "En cas d'échec réseau, il reprend le dernier cache avec un avertissement. `index:COMP` / `etf:SPY` forcent la classe d'actif quand un code est ambigu. "
                  "Les graphiques se font en deux étapes : récupérer, puis rendre ; indiquez la période avec `--start` / `--end`."),
    manual_fonts=("Polices : Inter, Source Sans 3 et Droid Sans sont fournies et intégrées pour les caractères latins ; le chinois utilise la police système en chinois traditionnel. "
                  "Les substitutions par rapport aux polices d'origine sont documentées dans le [guide des modèles](references/institutional-tables.md). Les polices propriétaires des PDF de référence ou de macOS ne sont pas distribuées."),
    h_test="Tests et évaluations",
    test_text=("`python3 -m unittest discover -s tests -v` exécute des tests à réponses connues pour les rendements, le drawdown, la volatilité, le routage des symboles, la fraîcheur du cache, l'import CSV, les styles de tableau et les calculs de résultats. "
               "La CI les exécute sous Ubuntu, macOS et Windows (Python 3.9 et 3.13), régénère les exemples pour vérifier qu'ils n'ont pas changé, lance un test de fumée en direct sur Nasdaq et installe les skills sur les trois systèmes. "
               "[evals/](evals/README.md) contient des demandes d'agent réalistes et les premiers résultats. Les README et le site sont générés par `python3 tools/build_docs.py`, et un test échoue s'ils sont périmés."),
    h_disc="Avertissement",
    disc="Ce projet met en forme des données et ne fournit aucun conseil en investissement. Sauf indication contraire dans la note de la galerie, les exemples utilisent des sociétés fictives et des valeurs synthétiques. Les dispositions de rapport sont des modèles indépendants, pas des rapports publiés par les institutions citées.",
    h_lic="Licence",
    star="⭐ Si cela vous fait gagner du temps, une étoile aide d'autres personnes à le trouver.",
    hero_a="Tableaux façon étude,", hero_b="graphiques et résultats.",
    site_sub="Tableaux et graphiques de cours de style institutionnel, plus analyses de résultats trimestriels de style HSBC construites à partir des documents d'origine. Anglais et chinois traditionnel, PNG + HTML.",
    cta1="Installer en une ligne", cta2="Voir sur GitHub", cta3="Démo résultats",
    t_modes="Choisissez une disposition",
    t_earn="Résultats trimestriels, depuis le document d'origine",
    earn_btn="Ouvrir la démo", t_data="D'où viennent les chiffres",
    tab_unix="macOS / Linux", tab_win="Windows", or_agent="Ou laissez votre agent IA le faire", copy="Copier", copied="Copié",
    docs_label="Docs", foot="Licence MIT. À titre d'illustration, pas un conseil en investissement.",
)
