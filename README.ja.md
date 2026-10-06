[English](README.md) · [简体中文](README.zh-CN.md) · **日本語** · [Français](README.fr.md)

# schwab-table

銘柄リスト、証券口座の保有銘柄スクリーンショット、または既存の騰落率・順位データを、Charles Schwab のリサーチレポート風のパフォーマンス表に変換する Claude Skill です。中国語版と英語版の両方を出力します（PNG + HTML）。

![サンプル](examples/neural9_en.png)

## 3 つのモード

| モード | 入力 | 2〜5 列目 |
|---|---|---|
| A ランキング表 | 各銘柄の YTD と、S&P 500 / NASDAQ 内での順位 | YTD、S&P 500 騰落率順位、S&P 500 寄与度順位、NASDAQ 騰落率順位 |
| B 保有銘柄表 | 証券口座の保有銘柄スクリーンショットまたはエクスポート | 建玉損益 %、当日損益、平均取得単価、保有株数 |
| C ウォッチリスト表 | ティッカーのみ | 年初来、直近 1 か月、直近 1 年、最新終値 |

## データソース

信頼できるデータのみを使用します。取引所の公式終値、指数提供会社（S&P Dow Jones Indices、Nasdaq Global Indexes。FRED 経由も可）、企業の IR / SEC 提出書類、またはユーザー自身の証券口座データです。リターンは公式終値から計算し、集約サイトの既製の騰落率は使いません。詳細は [SKILL.md](SKILL.md) を参照してください。

## ファイル

- `SKILL.md`：Skill の説明（構成、ビジュアル仕様、データソース規定、チェックリスト）
- `render_table.py`：レンダラー。JSON spec を読み込み、中国語・英語の HTML と 2x PNG を出力します
- `examples/`：モード A のサンプル（Charles Schwab が公開しているチャートのデータ、2026 年 10 月 2 日時点）

## インストール

フォルダごと Claude の skills ディレクトリに置くか、claude.ai の Skills 設定からアップロードしてください。

## 手動レンダリング

```bash
pip install playwright && playwright install chromium
python3 render_table.py examples/neural9_spec.json out/neural9
```

フォント：英数字は Inter、中国語は Noto Sans CJK SC / Source Han Sans SC を使用します。未インストールの場合は Helvetica Neue / PingFang にフォールバックします。

## 免責事項

このプロジェクトは表のスタイルを生成するだけで、投資助言は行いません。表中のデータは例示のみを目的としています。

## ライセンス

[MIT](LICENSE)
