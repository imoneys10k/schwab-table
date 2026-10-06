---
name: schwab-performance-table
description: 把股票清单、券商持仓截图或现成的涨跌幅/排名数据，做成 Charles Schwab 研报风格的业绩表（中英双语 PNG + HTML）。
---

# Schwab 风格股票业绩表

## 何时使用
用户想把一组股票做成 Schwab 研报里那种「浅蓝标题表头 + 灰色细分隔线 + 小字免责脚注」的表格。默认同时输出**中文版和英文版**，每版一个 HTML，再用 Playwright 以 2x 渲染成 PNG。

## 第一步：判断模式

| 模式 | 用户给了什么 | 标题 | 第 2–5 列 |
|---|---|---|---|
| A 排名表 | 每只股票的 YTD 和 S&P 500 / NASDAQ 内排名（原版 Schwab 表） | `{年份} {组合名} Performance` / `{年份} 年{组合名}表现` | YTD (%)、S&P 500 Performance rank、S&P 500 Contribution rank、NASDAQ Performance rank |
| B 持仓表 | 券商持仓截图或导出（成本、数量、盈亏） | `{年份} Portfolio Performance` / `{年份} 年持仓表现` | 开仓盈亏 (%)、当日盈亏 ($)、平均成本 ($)、持股数 |
| C 自选股表 | 只有一串股票代码（如「NVDA AMD MU 做个表」） | `{年份} Watchlist Performance` / `{年份} 年自选股表现` | 年初至今 (%)、近 1 月 (%)、近 1 年 (%)、最新收盘价 ($) |

判断不出来时问一句；用户只报代码、没给任何数字，就是模式 C。

## 第二步：准备数据

### 通用规则
- 每只股票必须有 `ticker`、英文全称、中文通用名。没有通用中文名的（如部分 ETF）中文版保留英文品牌名，可把描述词译出来（`Roundhill 新云 ETF`）
- 所有数据必须是同一个截止日（`as_of`）。不同来源日期对不上时，统一到最早的那个共同日期，不要混用

### 模式 A
- 排名字段缺失时先问用户；用户确认没有的填 `NA`
- 基准行：`NASDAQ`、`S&P 500`，三个排名列填 `NA`

### 模式 B（持仓截图）
- 从截图读：代码、开仓盈亏 %、当日盈亏、成本、数量；总计行的盈亏 %、当日盈亏；账户净值、开仓盈亏金额（写进脚注）
- 截图里的「交易价格」通常就是成本价，不是现价，不要当成现价
- 「组合合计」行担任基准行角色：加粗、按盈亏 % 插入排序位置，成本和持股数填 `NA`
- `as_of` 取截图对应的**最近一个美股收盘日**（台北/北京上午截图 = 前一个美东交易日）

### 模式 C（只有代码）
- 由 Claude 按下面的「数据源规定」取官方收盘价，自己计算 YTD、近 1 月、近 1 年回报
- 股票超过 15 只时，先跟用户确认是否全放，表格太长会失去研报感

## 数据源规定：只用权威数据

「权威」指数据的**原始发布方**，或者原样转载发布方数据并注明出处的官方机构。聚合网站、行情 App、财经博客一律不算。

### 1. 允许的来源
| 数据 | 权威来源 | 怎么取 |
|---|---|---|
| 用户自己的数据 | 用户上传的券商截图、券商导出文件、券商官网页面 | 直接用，不改写 |
| 个股收盘价 | 上市交易所的官方收盘价：Nasdaq.com 历史行情（含 NYSE 上市股票的综合收盘价）、NYSE.com | 页面是 JS 渲染，WebFetch 取不到，用 Claude in Chrome 打开 `https://www.nasdaq.com/market-activity/stocks/{ticker}/historical` 读表 |
| 个股收盘价（备选） | 用户的券商（如 Schwab 官网行情/研究页，需用户登录） | Claude in Chrome |
| S&P 500 | S&P Dow Jones Indices；或 FRED 原样转载（序列 `SP500`，注明来源 S&P Dow Jones Indices） | WebFetch `https://fred.stlouisfed.org/series/SP500` |
| 纳斯达克综合指数 | Nasdaq Global Indexes；或 FRED 原样转载（序列 `NASDAQCOM`） | WebFetch `https://fred.stlouisfed.org/series/NASDAQCOM` |
| 拆股、公司正式名称 | 公司 IR 公告、SEC EDGAR 文件 | WebFetch / WebSearch 限定官方域名 |
| 指数内排名（模式 A） | 只接受用户提供（来自 Schwab、Bloomberg 等） | 不自己算 |

### 2. 禁止的来源
- ChartRow、stockanalysis.com、Yahoo Finance、Google Finance、Investing.com、MarketBeat、Seeking Alpha、Stocktwits 等聚合站（实测 Google Finance 会给出过期价格）
- 论坛、博客、自动生成的 SEO 页面、AI 摘要
- 模型记忆里的任何数字
- 找不到权威来源时**不降级**到上述来源，改为：停下来告诉用户缺哪只、缺什么，请用户提供（如从 Schwab 导出），或该格填 `NA` 并在回复中说明

### 3. 由官方收盘价自己计算回报
网页上现成的「YTD %」大多来自聚合站，不直接采用。统一用官方收盘价计算：
- **YTD** = 截止日收盘价 ÷ 上一年最后一个交易日收盘价 − 1
- **近 1 月** = 截止日收盘价 ÷ 一个月前同日收盘价 − 1（该日休市则取之前最近一个交易日）
- **近 1 年** = 同上，取一年前
- 计算区间内有拆股/合股的，按 IR 公告的比例调整旧价格
- 口径一律为**价格回报**（不含股息），与 S&P 500、纳斯达克综合指数的口径一致
- 计算用代码完成并保留原始收盘价，回复里附上用到的两个价格，便于核对

### 4. 截止日对齐
- 全表必须同一截止日，取所有来源都已更新到的最近一个交易日
- 某只取不到该日官方收盘价，就从表里拿掉并在回复中说明，不用别的日期凑

### 5. 记录
- 脚注写原始发布方，例如：`Source: Nasdaq (official closing prices), S&P Dow Jones Indices, Nasdaq Global Indexes via FRED, as of 10/2/2026. Returns are price returns calculated from official closing prices.`
- 回复末尾列出每个数据页面的链接

## 第三步：表格结构（自上而下 4 个区块，5 列）

### 列
| # | 对齐 | 宽度 | 内容 |
|---|---|---|---|
| 1 | 左 | 30% | `{名称} ({TICKER})`，表头留空 |
| 2 | 右 | 13% | 主指标（排序依据） |
| 3–5 | 右 | 各 19% | 其余指标 |

- **第 1 列必须带股票代码**，中英文版都要：`Micron Technology Inc (MU)`、`美光科技 (MU)`
- 基准行、合计行不带代码
- 名称本身不再带括号：写 `谷歌 (GOOG)`，不写 `Alphabet（谷歌）(GOOG)`

### 1. 标题行
- 浅蓝底，与表头是同一条连续色带，中间无分隔线
- 加粗、深海军蓝，在整张表宽度上居中

### 2. 表头（两行）
- 底色同标题；加粗、深海军蓝、右对齐、底部对齐
- 第 1 行写分组或修饰词，第 2 行写指标名和单位
- **每行都不能折行**，太长就拆成两行。常用拆法：

| 英文 | 中文 |
|---|---|
| — / `YTD (%)` | `年初` / `至今 (%)` |
| `1-month` / `return (%)` | `近 1 月` / `涨跌幅 (%)` |
| `1-year` / `return (%)` | `近 1 年` / `涨跌幅 (%)` |
| `Last` / `price ($)` | `最新` / `收盘价 ($)` |
| `Open` / `P/L (%)` | `开仓` / `盈亏 (%)` |
| `Day` / `P/L ($)` | `当日` / `盈亏 ($)` |
| `Avg` / `cost ($)` | `平均` / `成本 ($)` |
| — / `Shares` | — / `持股数` |
| `S&P 500` / `Performance rank` | `标普 500` / `涨幅排名` |
| `S&P 500` / `Contribution rank` | `标普 500` / `贡献排名` |
| `NASDAQ` / `Performance rank` | `纳斯达克` / `涨幅排名` |

- 单位只写在表头，单元格内不写 `%` 或 `$`

### 3. 数据区
- 白底；行间 1px 浅灰横线，无竖线
- 全部行（股票 + 基准/合计）按第 2 列从高到低排序，基准行插在自己的位置上，不置顶也不置底
- 普通行常规字重、中灰；基准/合计行加粗、颜色更深
- 数字格式：百分比 1 位小数；金额 2 位小数加千分位；排名为整数不加千分位；负数用 `-`，正数不加 `+`；持股数按原始精度
- 缺失值写 `NA`

### 4. 脚注
- 表格下方，左对齐，与表同宽，小号灰字，自动换行
- 依次写：来源与截止日 → 本表指标的定义 → 免责声明 → 加粗的最后一句
- 模式 A 英文模板：

> Source: {source}, as of {as_of}. Performance rank based on performance within the respective index. Contribution rank (not available for NASDAQ) represents price performance multiplied by weight in index. All corporate names and market data shown above are for illustrative purposes only and are not a recommendation, offer to sell, or a solicitation of an offer to buy any security. Indexes are unmanaged, do not incur management fees, costs and expenses and cannot be invested in directly. **Past performance is no guarantee of future results.**

- 模式 B、C 把中间的指标定义换成本表的指标；没有指数行时去掉「Indexes are unmanaged…」那句
- 中文版完整翻译，最后一句为加粗的「过往业绩不代表未来表现。」

## 视觉参数（表宽 760px，取色为估计值）
| 元素 | 值 |
|---|---|
| 英文/数字字体 | `Inter`，回退 `Helvetica Neue`, Helvetica, Arial |
| 中文字体 | `Noto Sans CJK SC` / `Source Han Sans SC`（思源黑体），回退 `PingFang SC`, `Microsoft YaHei` |
| 数字列 | `font-feature-settings: "tnum" 1`（等宽数字）；负号单独用 `"tnum" 0` 包住，避免出现 `- 8.56` |
| 标题/表头底色 | `#ACDCEC` |
| 标题/表头文字 | `#1B2A4A`；标题 15px / 700，表头 13.5px / 600，行高 1.25 |
| 普通行 | `#595959`，13.5px，行高 26px |
| 基准/合计行 | `#2B2B2B`，600 |
| 行分隔线 | 1px `#D9D9D9` |
| 单元格内边距 | 左 10px，右 12px |
| 外框 | 1px `#D0D0D0` |
| 脚注 | 英文 10px / 中文 10.5px，`#6B6B6B`，行高 1.4，上方留 7px |

## 第四步：渲染
1. 把数据写成 spec JSON（格式见下）
2. 运行 `python3 render_table.py spec.json {输出前缀}`，生成 `{前缀}_en.html/.png` 和 `{前缀}_zh.html/.png`
3. 打开两张 PNG 对照自查清单，有问题改 spec 重渲
4. 交付两张 PNG（HTML 一并给，方便改）

spec 格式：
```json
{
  "langs": {
    "en": {"title": "...", "h1": ["", "", "1-month", "1-year", "Last"],
           "h2": ["", "YTD (%)", "return (%)", "return (%)", "price ($)"],
           "foot": "Source: ... <b>Past performance is no guarantee of future results.</b>", "foot_size": "10px"},
    "zh": {"title": "...", "h1": [...], "h2": [...], "foot": "...<b>过往业绩不代表未来表现。</b>", "foot_size": "10.5px"}
  },
  "formats": ["pct", "pct", "pct", "money"],
  "rows": [
    {"ticker": "NVDA", "name": {"en": "NVIDIA Corp", "zh": "英伟达"}, "cells": [25.7, 4.4, 24.2, 233.95]},
    {"name": {"en": "S&P 500", "zh": "标普 500"}, "cells": [12.8, null, null, null], "bench": true}
  ]
}
```
`formats`：`pct` 一位小数，`money` 两位小数加千分位，`raw` 原样输出（排名、持股数用它）。`null` 显示为 `NA`。

可选参数：`--langs en` 只渲染指定语言；`--no-png` 只写 HTML，不需要 Playwright。

没有 `render_table.py` 时，按上面的结构和视觉参数手写单文件 HTML，用 Playwright `device_scale_factor=2` 截 `#wrap` 容器。

## 自查清单
- [ ] 模式判断正确，列与模式一致
- [ ] 中英文两版都已输出
- [ ] 每只股票都带 `(TICKER)`，基准/合计行不带
- [ ] 所有数据来自权威来源，无聚合站数据
- [ ] 所有数据同一截止日，脚注日期、来源、回报口径正确
- [ ] 按第 2 列降序，基准/合计行在正确位置、加粗
- [ ] 表头无折行；单元格无 `%`、`$`；负号无空隙
- [ ] 标题与表头是一条连续浅蓝色带
- [ ] 脚注最后一句加粗
- [ ] 不画原截图左上角的「Legend」浮标（截图残留）
