# AHC074 商品紙兼務比較器：一連の研究記録（2026年11月）

> **研究資料のPRです。提出推奨ソルバの切替ではありません。** ベースの `solutions/*` や共有スクリプトは変更せず、再現可能な履歴・数値・ソースを独立パスに収録します。

## 結論

「担当のない汎用専用紙は0枚」とし、階段状の列に専用紙・共有紙を置き、さらに実商品の印刷色を持つ6枚を比較器として兼用する構成を実装した。100ケース各1024注文（合計102,400注文）に対する保存済み報告では、初版 **11.485166手**から、最良v6の **10.177646手**まで改善した（−1.307520手）。

**ただし元の6枚汎用紙版の参照値10.093223手より0.084423手多く、10.0手以下は未達。** またv5以降は、比較器6枚の担当商品を別の通常商品紙も担当する「重複担当」を許す。背景6枚＋普通の商品紙185枚＋キャップ1枚で、元の汎用紙構成から物理的な6枚を節約できたわけではない。**「専用の汎用紙0枚」と「汎用機能なし」を混同しない。**

公式Rust testerの完走を示すものではない。研究中の独立C++出力再生器・Python対話検査器では表示誤り／不正操作0を確認したが、**AtCoder 2秒制限の提出版としては未完成**（v6強化版のローカル直列4ケース平均2.634秒）。

## 歴代の100ケース比較

| 方式 | 主要変更 | 総手数 | 平均手数／注文 |
| --- | --- | ---: | ---: |
| 既存 `esw-clean.cpp` | 汎用紙6枚、共有紙とハンドル列 | 1,033,546 | **10.093223** |
| 初版 | 商品紙だけで全目標補完、追加穿孔 | 1,176,081 | 11.485166 |
| v2 | 常設3列2枚ずつの背景＋他方式からの設計選択 | 1,162,853 | 11.355986 |
| v3 | 比較商品紙6枚1列、720通りの背景 | 1,089,257 | 10.637275 |
| v4 | 商品紙2枚を共同で比較器へ差し込む | 1,070,010 | 10.449316 |
| v5 overlap | 背景商品に主紙重複、専用ハンドル撤廃 | 1,053,299 | 10.286123 |
| **v6** | 背景印刷と担当商品の潜在一致を共同最適化 | **1,042,191** | **10.177646** |

初版からv6への改善は平均1.307520手。v3以降の大きな前進は「720順列比較器」→「2枚共同差込み」→「重複担当で追加穿孔0」→「背景・担当の共設計」。v5の一意担当版は10.401777手で、v5 overlapとは別の方式。

**履歴上の訂正：** 後半の一報には「v5が最良」とする誤記がある。正しい採用比較基準は **v6＝10.177646手／注文**。一部の8ケース平均10.170776などは100ケース値ではない。

## 研究で棄却・保留した構造

- 5枚・7枚比較器、分割比較器、比較窓の多枚印刷、3商品共有、専用主紙の複製、専用ハンドル／補完列変更、未来費用を近似した列再設計、追加穿孔の近似最適化などは、当該実装・当該測定集合で0.1手級の改善を確認できなかった。
- **協力必須共有ペア**（背景だけでは不可能だが別の商品紙との共同補完なら可能）は、研究Dで実際に作って合法に処理できた。ただし実手数は悪化しており、安い協力ペアを多数設計する段階には至っていない。
- 最良版の改善を後半の小規模の「わずかな改善」で上書きしていない。設定ごとに4／8／20ケースなど評価範囲が違うので、必ず原報告の表記を参照。

## 原報告と集計CSV（10回分すべてを原文で保管）

| 区分 | レポート | 集計CSV |
| --- | --- | --- |
| 初回 | [詳細](reports/ahc074_no_generic_report_ja.md) | [CSV](results/ahc074_no_generic_results.csv) |
| v2 | [詳細](reports/ahc074_product_only_v2_report_ja.md) | [CSV](results/ahc074_product_only_v2_results.csv) |
| v3 | [詳細](reports/ahc074_product_only_v3_report_ja.md) | [CSV](results/ahc074_product_only_v3_results.csv) |
| v4 | [詳細](reports/ahc074_product_only_v4_report_ja.md) | [CSV](results/ahc074_product_only_v4_results.csv) |
| v5 | [詳細](reports/ahc074_product_only_v5_report_ja.md) | [CSV](results/ahc074_product_only_v5_results.csv) |
| v6 | [詳細](reports/ahc074_product_only_v6_report_ja.md) | [CSV](results/ahc074_product_only_v6_results.csv) |
| 研究A | [詳細](reports/ahc074_v6_research_report_ja.md) | [CSV](results/ahc074_v6_research_results.csv) |
| 研究B | [詳細](reports/ahc074_product_only_v7_research_report_ja.md) | [CSV](results/ahc074_product_only_v7_research_results.csv) |
| 研究C | [詳細](reports/ahc074_v7_research_report_ja.md) | [CSV](results/ahc074_v7_research_results.csv) |
| 研究D | [詳細](reports/ahc074_product_only_v8_research_report_ja.md) | [CSV](results/ahc074_product_only_v8_research_results.csv) |

各レポートの保存出力、構築失敗フラグ、単体検証器、試作パラメータ、コンパイル方法などの細部は原報告に記載。ZIPで別途配布したバイナリ・大量の全注文出力は、このGit差分には混ぜない。

## ソースと再現

- 最良研究版：[`solutions/product-only-v6-research/main.cpp`](../../../solutions/product-only-v6-research/main.cpp)。必ず [解法README](../../../solutions/product-only-v6-research/README.md) の「実行時間・採用不可の留保」を読むこと。
- 各世代と不採用のC++：[sources/](sources/) 以下に歴史的実装を置く。**研究用なので提出可能性は個別に要確認**（5枚背景試作には構築失敗がある）。
- 同一リポジトリで再検証する場合は `scripts/pahcer_run.py --compare solutions/<既存版> solutions/product-only-v6-research --seeds 0-100 -c "product-only research"` を使う。このPR作成作業では公式2000ケース評価を新たに実行しておらず、上記は**再現手順の提案**。リポジトリ固有の計時条件は [AGENTS.md](../../../AGENTS.md) に従う。
