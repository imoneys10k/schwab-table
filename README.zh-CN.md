[English](README.md) · **简体中文** · [日本語](README.ja.md) · [Français](README.fr.md)

# schwab-table

一个 Claude Skill：把股票清单、券商持仓截图或现成的涨跌幅/排名数据，做成 Charles Schwab 研报风格的业绩表，同时输出中文版和英文版（PNG + HTML）。

![示例](examples/neural9_zh.png)

## 三种模式

| 模式 | 输入 | 第 2–5 列 |
|---|---|---|
| A 排名表 | 每只股票的 YTD 和 S&P 500 / NASDAQ 内排名 | YTD、S&P 500 涨幅排名、S&P 500 贡献排名、NASDAQ 涨幅排名 |
| B 持仓表 | 券商持仓截图或导出 | 开仓盈亏 %、当日盈亏、平均成本、持股数 |
| C 自选股表 | 只有股票代码 | 年初至今、近 1 月、近 1 年、最新收盘价 |

## 数据源

只用权威数据：交易所官方收盘价、指数编制方（S&P Dow Jones Indices、Nasdaq Global Indexes，可经 FRED 转载）、公司 IR / SEC 文件，或用户自己的券商数据。回报由官方收盘价计算，不采用聚合网站上的现成涨跌幅。详见 [SKILL.md](SKILL.md)。

## 文件

- `SKILL.md`：Skill 说明（结构、视觉参数、数据源规定、自查清单）
- `render_table.py`：渲染器，读 JSON spec，输出中英文 HTML 和 2x PNG
- `examples/`：模式 A 示例（数据来自 Charles Schwab 公开图表，截至 10/2/2026）

## 安装

把整个文件夹放进 Claude 的 skills 目录，或在 claude.ai 的 Skills 设置里上传。

## 手动渲染

```bash
pip install playwright && playwright install chromium
python3 render_table.py examples/neural9_spec.json out/neural9
```

字体：英文和数字用 Inter，中文用思源黑体（Noto Sans CJK SC / Source Han Sans SC），没有安装时回退到 Helvetica Neue / PingFang。

## 免责声明

本项目只生成表格样式，不提供任何投资建议。表中数据仅作示例。

## 许可证

[MIT](LICENSE)
