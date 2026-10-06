---
name: schwab-performance-table
description: 把股票清单、券商持仓截图或现成的涨跌幅/排名数据，做成 Charles Schwab 研报风格的业绩表（排名表、持仓盈亏表、自选股表）；也能画若干标的（最多 9 只）在任意时间段的走势图，含回撤、基准对比、对数刻度（中英双语 PNG + HTML）。只要用户提到业绩表、持仓表、自选股表、走势图、涨幅对比、回撤，或要做研报风格的股票表格/图、公众号或 PPT 里的股票配图，就使用这个 skill，即使没有明确提到 Schwab。
---

# Schwab 风格股票业绩表

## 何时使用
用户想把一组股票做成 Schwab 研报里那种「浅蓝标题表头 + 灰色细分隔线 + 小字免责脚注」的表格。默认同时输出**中文版和英文版**，每版一个 HTML，再用 Playwright 以 2x 渲染成 PNG。

要画**走势图**（若干标的在某个时间段内的走势）时，直接看文末的「走势图模式」。

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
- `as_of`：截图自带时间戳时以它为准。数字是盘中值（美东盘中截图）就如实写「as of {时间}，价格有延迟」，**不要写成收盘日**；截图没有时间戳时，取对应的**最近一个美股收盘日**（台北/北京上午截图 = 前一个美东交易日）
- 合计行和各行对不上（可能含表外持仓或现金）时，**照券商原样显示，不要自行修正**；在脚注或回复里说明，并把你算出的差异告诉用户

### 模式 C（只有代码）
- 优先用 `fetch_prices.py` 取官方收盘价（比开浏览器快、可复现），`--start` 要早于一年多前才算得出近 1 年，例如 `python3 fetch_prices.py NVDA AMD MU --start 2025-09-01 -o data/x.json`；再按下面的「数据源规定」自己计算 YTD、近 1 月、近 1 年回报。取不到时才退回 Claude in Chrome
- 用户没提基准就不加基准行；用户要对比时，可用 `--benchmark SPY,COMP` 取基准，并说明 SPY 只是标普 500 的替代
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

可选参数：`--langs en` 只渲染指定语言；`--no-png` 只写 HTML，不需要 Playwright；`--scale 3` 提高 PNG 清晰度（默认 2）。

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

---

# 走势图模式：若干标的在历史时间段内的走势

## 何时使用
用户要看一只或多只标的在某个时间段内的走势、累计涨跌或回撤（例如「画一下 NVDA、MU 今年的走势」「这几只 3 月到 6 月的走势对比」）。风格与业绩表一致：浅蓝标题带、灰色细线、小字脚注，默认输出**中文和英文两版**（PNG + HTML）。最多 **9 只**标的，另可带一条基准。

## 流程
1. **确定标的和时间段。** 用户给了起止日就严格照用；没说就是**年初至今**。起点取起始日当天或之前最近一个收盘价记为 100（年初至今即上年最后一个交易日的收盘价）
2. **取数据**（唯一数据源是 Nasdaq 官方历史行情接口）：
   ```bash
   python3 fetch_prices.py NVDA MU AAPL --start 2026-01-01 --end 2026-10-02 -o data/watch.json
   ```
   - 数据是交易所官方日收盘价，已按拆股复权、不含股息，即**价格回报**；约有 10 年日线。股票、ETF、纳斯达克指数（`COMP`、`NDX`）都能取
   - 基准默认 **SPY**（标普 500 的 ETF，同一来源，图和脚注会标明它只是指数的替代）。`--benchmark COMP` 用纳斯达克综合指数；`--benchmark SP500` 走 FRED 转载的标普 500 指数（FRED 偶尔超时）；`--benchmark none` 不画基准
   - 多个基准用逗号分隔：`--benchmark SPY,COMP`。`COMP`、`NDX` 等是指数，脚本直接按指数查（同样的字母也可能是美股代码，例如 COMP 是 Compass 公司）；代码有歧义时用 `index:COMP`、`etf:SPY`、`stock:XXX` 指定类别
   - **只覆盖美股。** 港股、A 股等 Nasdaq 没有的市场：请用户提供 CSV（券商或交易所导出），用 `python3 csv_to_prices.py 0700.HK=tencent.csv --benchmark HSI=hsi.csv -o data/hk.json` 转换，来源会记为「用户提供的数据」。不要改用聚合站
   - **总回报：** Nasdaq 的分红数据没有按拆股调整，ETF 也没有分红，所以不能自动算总回报。用户自己提供带 `Adj Close` 的 CSV 时，用 `csv_to_prices.py --adj-close`，图会标注为总回报。价格回报和总回报不能画在同一张图里
   - 响应缓存 12 小时（`--refresh` 绕过）。网络失败时会带警告地用上一次缓存，脚注里的获取日期就是缓存实际获取的日期
   - 聚合站和模型记忆里的数字一律不用。脚本以退出码 2 结束、或 JSON 里 `errors` 非空，说明有标的没取到：**停下来告诉用户缺哪只**，不要自己补数
   - 公司名由 Claude 提供（英文全称 + 通用中文名），写进 spec 的 `names`
3. **写 spec**（格式见下），运行：
   ```bash
   python3 render_chart.py spec.json out/watch
   ```
   生成 `out/watch_en.html/.png` 和 `out/watch_zh.html/.png`
4. 打开两张 PNG，对照自查清单；有问题改 spec 重渲。交付两张 PNG（HTML 一并给）

## 版式
| `layout` | 内容 | 适用 |
|---|---|---|
| `auto`（默认） | 5 只及以下用 `lines`，6–9 只用 `multiples` | 一般情况 |
| `lines` | 折线图 + 回撤面板 + 汇总表 | 2–5 只 |
| `multiples` | 每只一个小图，**所有小图同一纵轴**，每个小图下带回撤条，灰色虚线为基准 | 6–9 只 |

- `y_scale`：`auto`（默认）、`linear`、`log`。`auto` 在最高与最低指数相差超过 3 倍时自动改用**对数刻度**，副标题会写明「对数刻度」
- `drawdown`：是否画回撤（默认开）；`table`：`lines` 版式是否带汇总表（默认开）

## 规格
- 纵轴统一用「起点 = 100」的指数，**一张图只有一个纵轴，不做双轴**
- **颜色按标的固定顺序，不随排名变化**：蓝 `#2a78d6`、橙 `#eb6834`、绿 `#1baf7a`、黄 `#eda100`、粉 `#e87ba4`（已通过色盲可分辨性检查）。基准固定深灰虚线 `#595959`。小图矩阵里个股统一海军蓝 `#1B2A4A`，基准浅灰虚线
- 线宽 2px（基准 1.6px 虚线）；线尾画圆点（2px 白圈），**线尾直接标注代码和涨跌幅**，挤在一起时错开并加小引线。绿、黄在白底上对比度偏低，所以直接标注和汇总表不能省
- 汇总表列：区间回报、年化波动率、最大回撤、最新价；按回报降序，基准行加粗，基准最新价填 `NA`
- 年化波动率 = 日价格回报的标准差 × √252；回撤 = 当日收盘价相对区间内至当日最高收盘价的跌幅；最大回撤 = 区间内回撤的最小值
- 脚注依次写：来源与截止日、数据获取日、起点、指标定义、基准替代说明（用 ETF 时）、免责声明、加粗末句
- 时间跨度决定横轴刻度：45 天内按周，约一年内按月，更长按季度或年

## spec 格式
```json
{
  "data": "data/watch.json",
  "symbols": ["NVDA", "MU"],
  "names": {"NVDA": {"en": "NVIDIA Corp", "zh": "英伟达"}, "MU": {"en": "Micron Technology Inc", "zh": "美光科技"}},
  "benchmark_name": {"en": "S&P 500 (SPY)", "zh": "标普 500 (SPY)"},
  "benchmarks": ["SPY", "COMP"], "colors": {"NVDA": "#2a78d6"},
  "layout": "auto", "y_scale": "auto", "drawdown": true, "table": true,
  "start": "2026-01-01", "end": "2026-10-02",
  "title": {"en": "...", "zh": "..."}, "note": {"en": "...", "zh": "..."}
}
```
除 `data` 外都是可选项。`start`、`end` 不写时用数据文件的范围；`note` 会放在脚注开头（示例里用来标注「虚构示例」）。`benchmarks` 选择并排序数据文件里的基准；`benchmark_name` 可以写成 `{"en": ..., "zh": ...}`（用于第一个基准），也可以按代码分别写；`colors` 用 `#rrggbb` 覆盖个别线条的颜色（默认配色已通过色盲可分辨性检查，改色后自行保证对比度）。命令行参数：`--langs en` 只出一种语言，`--no-png` 只写 HTML，`--pdf` 另存矢量 PDF，`--scale 3` 提高 PNG 清晰度（默认 2），`--theme dark` 输出深色主题（表格和图都支持）。HTML 文件里鼠标悬停在图上会显示当天各条线的数值。

## 自查清单（走势图）
- [ ] 标的不超过 9 只；时间段与用户要求一致（没说就是年初至今）
- [ ] 数据来自 `fetch_prices.py`（Nasdaq 官方收盘价），没有聚合站或记忆数字；没取到的标的已告知用户
- [ ] 中英文两版都已输出，脚注里的来源、截止日、起点正确
- [ ] 只有一个纵轴；颜色按标的固定；线尾有直接标注，标签不重叠、不被截断
- [ ] 用 ETF 做基准时，脚注写明它是替代；用对数刻度时，副标题写明
- [ ] 汇总表按回报降序，基准行加粗，数字与线尾标注一致
- [ ] 港股、A 股等非美股标的来自用户提供的 CSV，脚注写明「用户提供的数据」；总回报图只用于用户提供的复权价
