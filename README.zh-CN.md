[English](README.md) · **简体中文** · [日本語](README.ja.md) · [Français](README.fr.md)

# schwab-table

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE) [![install-test](https://github.com/imoneys10k/schwab-table/actions/workflows/install-test.yml/badge.svg)](https://github.com/imoneys10k/schwab-table/actions/workflows/install-test.yml)

一个 Claude Skill：把股票清单、券商持仓截图或现成的涨跌幅/排名数据，做成 Charles Schwab 研报风格的业绩表；还能用同样的风格画出若干标的在任意时间段内的走势图。全部同时输出中文版和英文版（PNG + HTML）。

![英文版](examples/neural9_en.png)

![中文版](examples/neural9_zh.png)

## 三种模式

| 模式 | 输入 | 第 2–5 列 | 示例 |
|---|---|---|---|
| A 排名表 | 每只股票的 YTD 和 S&P 500 / NASDAQ 内排名 | YTD、S&P 500 涨幅排名、S&P 500 贡献排名、NASDAQ 涨幅排名 | [EN](examples/neural9_en.png) · [中文](examples/neural9_zh.png) |
| B 持仓表 | 券商持仓截图或导出 | 开仓盈亏 %、当日盈亏、平均成本、持股数 | [EN](examples/holdings_en.png) · [中文](examples/holdings_zh.png) |
| C 自选股表 | 只有股票代码 | 年初至今、近 1 月、近 1 年、最新收盘价 | [EN](examples/watchlist_en.png) · [中文](examples/watchlist_zh.png) |

模式 A 的数据来自 Charles Schwab 公开图表；模式 B、C 的示例使用虚构公司和编造数字，仅作演示。

## 走势图

最多 9 只标的、任意时间段（默认年初至今），同样的研报风格，带回撤面板和汇总表，中英双版（PNG + HTML）。示例使用虚构公司和合成数据。

![线图](examples/chart_lines_zh.png)

![小图矩阵](examples/chart_multiples_zh.png)

| 版式 | 内容 | 适用 |
|---|---|---|
| `lines` | 折线图、回撤面板、汇总表 | 2–5 只 |
| `multiples` | 每只一个小图，同一纵轴，下方带回撤条 | 6–9 只 |

`layout: auto` 会按标的数量自动选择。

- **数据：** Nasdaq 官方历史行情接口：交易所官方日收盘价，已按拆股复权，价格回报，约 10 年。基准默认用 SPY，图上标注为标普 500 的替代。不使用其他来源。
- **纵轴：** 只有一个纵轴，起点为 100。涨幅差距很大时自动改用对数刻度（也可用 `y_scale` 手动指定）。

```bash
python3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 -o data/watch.json
python3 render_chart.py examples/chart_lines_spec.json out/chart   # copy and edit the spec for your own data
```

## 在 Claude 里使用

安装后直接用自然语言说就行，例如：

- 帮我给 NVDA、AMD、MU 做个业绩表。
- 把这张持仓截图做成 Schwab 风格的表。（附上截图）
- 用这份数据做一张 2026 年 Neural9 排名表。
- 帮我画 NVDA、MU、AAPL 今年的走势图。
- 把这六只股票 3 月到 6 月的走势用对数刻度对比一下。

## 数据源

只用权威数据：交易所官方收盘价、指数编制方（S&P Dow Jones Indices、Nasdaq Global Indexes，可经 FRED 转载）、公司 IR / SEC 文件，或用户自己的券商数据。回报由官方收盘价计算，不采用聚合网站上的现成涨跌幅。详见 [SKILL.md](SKILL.md)（中文原文；英文译本见 [SKILL.en.md](SKILL.en.md)）。

## 文件

- `SKILL.md`：Claude 实际加载的 Skill 说明（结构、视觉参数、数据源规定、自查清单）
- `SKILL.en.md`：`SKILL.md` 的英文译本，供人阅读
- `install.sh` / `install.ps1`：一键安装脚本（macOS / Linux 与 Windows）
- `render_table.py`：表格渲染器，读 JSON spec，输出中英文 HTML 和 2x PNG
- `fetch_prices.py`：从 Nasdaq 官方接口下载日收盘价（仅用标准库）
- `render_chart.py`：走势图渲染器，读取下载的价格和 JSON spec
- `fonts.py`、`fonts/`：随仓库附带的 Inter 字体（SIL OFL），嵌入每个 HTML 文件
- `requirements.txt`：Python 依赖（Playwright）
- `examples/`：三种表格模式和两种图表版式各一份 spec 和渲染结果（`sample_prices.json` 为合成数据）
- `assets/`：社交预览图

## 安装

支持 macOS、Linux 和 Windows。需要 Python 3.9+（用于渲染表格），git 可选。

### 让 AI Agent 帮你安装

把下面这段话直接发给 Claude Code、Codex 或其他编程 Agent：

```text
请帮我安装 https://github.com/imoneys10k/schwab-table 这个 skill。
先判断我的操作系统。macOS 或 Linux 运行：
  curl -fsSL https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.sh | sh
Windows 在 PowerShell 里运行：
  irm https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.ps1 | iex
如果我用的不是 Claude，请装到那个 Agent 自己的 skills 目录
（macOS/Linux 在 `sh -s --` 后面加 `--dir <路径>`；Windows 先保存 install.ps1，再用 -Dir <路径> 运行）。
装完确认输出了 "Render OK"，然后提醒我重启，让 skill 生效。
```

### 或者自己运行

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.sh | sh
```

Windows（PowerShell）：

```powershell
irm https://raw.githubusercontent.com/imoneys10k/schwab-table/main/install.ps1 | iex
```

安装脚本会把 skill 放进 `~/.claude/skills/schwab-performance-table`（Windows 为 `%USERPROFILE%\.claude\skills\...`），在里面创建独立的 Python 虚拟环境，安装 Playwright 和 Chromium（约 100 MB），再渲染一张示例表做冒烟测试。一切正常时会输出 `Render OK`。装完重启 Claude，skill 才会被加载。想先看脚本内容，可以打开 [install.sh](install.sh) 或 [install.ps1](install.ps1)。

| 选项（macOS / Linux） | 选项（Windows） | 作用 |
|---|---|---|
| `--dir PATH` | `-Dir PATH` | 装到别处（比如其他 Agent 的 skills 目录）。环境变量 `CLAUDE_SKILLS_DIR` 可修改默认根目录 |
| `--skip-deps` | `-SkipDeps` | 跳过 Python / Playwright / Chromium，只下载文件 |

用管道运行时，选项要放在 `sh -s --` 后面，例如 `curl -fsSL .../install.sh | sh -s -- --dir ~/my-skills/schwab`。Windows 请先保存 `install.ps1`，再运行 `.\install.ps1 -Dir C:\path`。

**更新：** 再运行一遍同样的命令。**卸载：** 删除安装目录。

**常见问题：** Debian/Ubuntu 需要先装 `python3-venv`；Linux 上 Chromium 启动失败时，运行 `sudo <安装目录>/.venv/bin/python -m playwright install-deps chromium`。

## 手动渲染

如果用安装脚本装的，`render_table.py` 会自动切换到它的虚拟环境，直接 `python3 render_table.py ...` 就行。否则需要 Python 3.9 及以上：

```bash
pip install -r requirements.txt && playwright install chromium
python3 render_table.py examples/neural9_spec.json out/neural9
```

可选参数（两个渲染器通用）：`--langs en` 只渲染指定语言（逗号分隔）；`--no-png` 只写 HTML，不需要 Playwright；`--scale 3` 提高 PNG 清晰度（默认 2，即 1520 px 宽）。输出目录不存在时会自动创建。

走势图分两步：先下载价格，再渲染。用 `--start` / `--end` 指定时间段，默认年初至今；`--benchmark COMP` 可把基准从 SPY 换成纳斯达克综合指数。

```bash
python3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 -o data/watch.json
python3 render_chart.py examples/chart_lines_spec.json out/chart   # copy and edit the spec for your own data
```

字体：Inter（随仓库放在 `fonts/`，SIL 开源字体许可）会嵌入每个 HTML 文件，用于英文和数字，所以在任何机器上效果一致。中文使用系统自带的中文字体（macOS 为苹方，Windows 为微软雅黑）。精简的 Linux 服务器上请先装一个，例如 `sudo apt install fonts-noto-cjk`，否则中文版会显示成方块。

## 免责声明

本项目只生成表格样式，不提供任何投资建议。表中数据仅作示例。

## 许可证

[MIT](LICENSE)
