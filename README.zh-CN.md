[English](README.md) · **简体中文** · [日本語](README.ja.md) · [Français](README.fr.md)

# schwab-table

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

一个 Claude Skill：把股票清单、券商持仓截图或现成的涨跌幅/排名数据，做成 Charles Schwab 研报风格的业绩表，同时输出中文版和英文版（PNG + HTML）。

![英文版](examples/neural9_en.png)

![中文版](examples/neural9_zh.png)

## 三种模式

| 模式 | 输入 | 第 2–5 列 | 示例 |
|---|---|---|---|
| A 排名表 | 每只股票的 YTD 和 S&P 500 / NASDAQ 内排名 | YTD、S&P 500 涨幅排名、S&P 500 贡献排名、NASDAQ 涨幅排名 | [EN](examples/neural9_en.png) · [中文](examples/neural9_zh.png) |
| B 持仓表 | 券商持仓截图或导出 | 开仓盈亏 %、当日盈亏、平均成本、持股数 | [EN](examples/holdings_en.png) · [中文](examples/holdings_zh.png) |
| C 自选股表 | 只有股票代码 | 年初至今、近 1 月、近 1 年、最新收盘价 | [EN](examples/watchlist_en.png) · [中文](examples/watchlist_zh.png) |

模式 A 的数据来自 Charles Schwab 公开图表；模式 B、C 的示例使用虚构公司和编造数字，仅作演示。

## 在 Claude 里使用

安装后直接用自然语言说就行，例如：

- 帮我给 NVDA、AMD、MU 做个业绩表。
- 把这张持仓截图做成 Schwab 风格的表。（附上截图）
- 用这份数据做一张 2026 年 Neural9 排名表。

## 数据源

只用权威数据：交易所官方收盘价、指数编制方（S&P Dow Jones Indices、Nasdaq Global Indexes，可经 FRED 转载）、公司 IR / SEC 文件，或用户自己的券商数据。回报由官方收盘价计算，不采用聚合网站上的现成涨跌幅。详见 [SKILL.md](SKILL.md)（中文原文；英文译本见 [SKILL.en.md](SKILL.en.md)）。

## 文件

- `SKILL.md`：Claude 实际加载的 Skill 说明（结构、视觉参数、数据源规定、自查清单）
- `SKILL.en.md`：`SKILL.md` 的英文译本，供人阅读
- `render_table.py`：渲染器，读 JSON spec，输出中英文 HTML 和 2x PNG
- `requirements.txt`：Python 依赖（Playwright）
- `examples/`：三种模式各一份 spec 和渲染结果
- `assets/`：社交预览图

## 安装

把仓库克隆到 Claude 的 skills 目录：

```bash
git clone https://github.com/imoneys10k/schwab-table.git ~/.claude/skills/schwab-performance-table
```

或者下载文件夹，在 claude.ai 的 Skills 设置里上传。

## 手动渲染

需要 Python 3.9 及以上。

```bash
pip install -r requirements.txt && playwright install chromium
python3 render_table.py examples/neural9_spec.json out/neural9
```

可选参数：`--langs en` 只渲染指定语言（逗号分隔）；`--no-png` 只写 HTML，不需要 Playwright。输出目录不存在时会自动创建。

字体：英文和数字用 Inter，中文用思源黑体（Noto Sans CJK SC / Source Han Sans SC），没有安装时回退到 Helvetica Neue / PingFang。

## 免责声明

本项目只生成表格样式，不提供任何投资建议。表中数据仅作示例。

## 许可证

[MIT](LICENSE)
