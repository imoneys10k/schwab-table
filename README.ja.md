[English](README.md) · [简体中文](README.zh-CN.md) · **日本語** · [Français](README.fr.md)

# schwab-table

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

銘柄リスト、証券口座の保有銘柄スクリーンショット、または既存の騰落率・順位データを、Charles Schwab のリサーチレポート風のパフォーマンス表に変換する Claude Skill です。中国語版と英語版の両方を出力します（PNG + HTML）。

![英語版](examples/neural9_en.png)

![中国語版](examples/neural9_zh.png)

## 3 つのモード

| モード | 入力 | 2〜5 列目 | サンプル |
|---|---|---|---|
| A ランキング表 | 各銘柄の YTD と、S&P 500 / NASDAQ 内での順位 | YTD、S&P 500 騰落率順位、S&P 500 寄与度順位、NASDAQ 騰落率順位 | [EN](examples/neural9_en.png) · [中文](examples/neural9_zh.png) |
| B 保有銘柄表 | 証券口座の保有銘柄スクリーンショットまたはエクスポート | 建玉損益 %、当日損益、平均取得単価、保有株数 | [EN](examples/holdings_en.png) · [中文](examples/holdings_zh.png) |
| C ウォッチリスト表 | ティッカーのみ | 年初来、直近 1 か月、直近 1 年、最新終値 | [EN](examples/watchlist_en.png) · [中文](examples/watchlist_zh.png) |

モード A は Charles Schwab が公開しているチャートのデータを使用しています。モード B・C のサンプルは架空の企業と作り物の数字で、例示のみを目的としています。

## Claude での使い方

インストール後は、普通の言葉で頼むだけです。例：

- NVDA、AMD、MU のパフォーマンス表を作って。
- この保有銘柄のスクリーンショットを Schwab 風の表にして。（スクリーンショットを添付）
- このデータで 2026 年 Neural9 のランキング表を作って。

## データソース

信頼できるデータのみを使用します。取引所の公式終値、指数提供会社（S&P Dow Jones Indices、Nasdaq Global Indexes。FRED 経由も可）、企業の IR / SEC 提出書類、またはユーザー自身の証券口座データです。リターンは公式終値から計算し、集約サイトの既製の騰落率は使いません。ルールの詳細は [SKILL.md](SKILL.md)（中国語）を参照してください。英語訳は [SKILL.en.md](SKILL.en.md) です。

## ファイル

- `SKILL.md`：Claude が実際に読み込む Skill の説明（構成、ビジュアル仕様、データソース規定、チェックリスト）。中国語
- `SKILL.en.md`：`SKILL.md` の英語訳（人が読む用）
- `render_table.py`：レンダラー。JSON spec を読み込み、中国語・英語の HTML と 2x PNG を出力します
- `requirements.txt`：Python の依存パッケージ（Playwright）
- `examples/`：3 つのモードそれぞれの spec と出力結果
- `assets/`：ソーシャルプレビュー画像

## インストール

リポジトリを Claude の skills ディレクトリにクローンします：

```bash
git clone https://github.com/imoneys10k/schwab-table.git ~/.claude/skills/schwab-performance-table
```

または、フォルダをダウンロードして claude.ai の Skills 設定からアップロードしてください。

## 手動レンダリング

Python 3.9 以上が必要です。

```bash
pip install -r requirements.txt && playwright install chromium
python3 render_table.py examples/neural9_spec.json out/neural9
```

オプション：`--langs en` は指定した言語のみレンダリングします（カンマ区切り）。`--no-png` は HTML のみを書き出し、Playwright は不要です。出力先フォルダがなければ自動で作成されます。

フォント：英数字は Inter、中国語は Noto Sans CJK SC / Source Han Sans SC を使用します。未インストールの場合は Helvetica Neue / PingFang にフォールバックします。

## 免責事項

このプロジェクトは表のスタイルを生成するだけで、投資助言は行いません。表中のデータは例示のみを目的としています。

## ライセンス

[MIT](LICENSE)
