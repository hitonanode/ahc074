# AHC074 — 紙枚数 K の感度実験（研究資料・提出非対応）

## 結論

提供された esw-clean.cpp（6枚の汎用紙＋キャップ1枚を維持）を K=182〜202 に可変化し、公式生成入力の同じ100 seed × 1024注文で比較しました。

- **192枚: 10.09322手/注文**
- **202枚: 9.88463手/注文**（−0.20859手、−2.067%、98/100ケース改善）
- **182枚: 10.55713手/注文**（＋0.46391手、＋4.596%）
- **192枚近傍の傾き: 追加1枚につき約0.02503手の削減**（seed単位95%CI: 0.02208〜0.02798）
- 全1,300ラン・1,331,200注文を独立C++チェッカーで再生し、誤表示・不正操作・操作数上限違反は **0件**。

本来の問題制約は K=192 であり、K>192の結果は反実仮想の感度測定です。新しい提出解法や9.5手達成を意味しません。使用した基準 esw-clean.cpp は会話で提供されたスナップショットで、現在の main の最良版とは限りません。

**[詳細レポート](REPORT_ja.md)** に全13水準の測定、区間推定、操作内訳、実行時間、設計上の示唆、検証を記録しました。

## 登録ファイル

| ファイル | 内容 |
|---|---|
| [REPORT_ja.md](REPORT_ja.md) | 原実験の詳細・結論・全数値表・解釈と制限 |
| [src/esw-paper-count.cpp](src/esw-paper-count.cpp) | 元ソルバの全体を収録。-DPAPER_COUNT=K で総紙数を切り替え |
| [src/paper-count.patch](src/paper-count.patch) | 提供された esw-clean.cpp からの変更だけ（K計算、共有ペア数、紙番号ビット集合） |
| [src/replay-checker.cpp](src/replay-checker.cpp) | 公式規則を独立実装し、全操作を可視性・表示一致まで確認 |
| [results/summary.csv](results/summary.csv) | 全13水準の平均・比較差・95%CI・実行時間・勝分敗 |
| [results/per_case.csv](results/per_case.csv) | 100 seed × 13水準の実測手数、対応差、操作内訳の主要指標、出力SHA256 |
| [results/paper_count_curve.svg](results/paper_count_curve.svg) / [results/paired_delta.svg](results/paired_delta.svg) | GitHubで表示できる平均と対応差のグラフ（記録済みCSVから再描画） |
| [scripts/reproduce.py](scripts/reproduce.py) | 既存 tools/in を使う再計測と独立検証の簡易ランナー |

元実験の約45MiBのZIPアーカイブ（全1,300ランの出力とstderr、入力、追加集計CSV・分析スクリプト、検証ログ）はChatGPT会話に添付済みです。Gitには巨大な生ログ・全操作列・既存の tools/in の重複を登録しません。再生検証可能な最終比較値は結果CSVに保存しています。調査中の他の solver・共通スクリプト・pahcer履歴は変更しません。

## 1ケースの手順（GCC、AVX2/BMI2を使えるx86-64環境）

リポジトリのルートから以下を実行します。

```sh
cd docs/experiments/paper-count-sensitivity-20261107
mkdir -p bin
g++ -std=c++20 -O2 -march=native -DLOCAL_BENCH -DPAPER_COUNT=192 src/esw-paper-count.cpp -o bin/esw-k192
g++ -std=c++20 -O2 src/replay-checker.cpp -o bin/replay-checker
bin/esw-k192 < ../../../tools/in/0000.txt > /tmp/ahc074-k192-0000.out
bin/replay-checker ../../../tools/in/0000.txt /tmp/ahc074-k192-0000.out 192
```

元のKを変える場合は、入力先頭行を置き換えます。バーコード・注文は変えません。

```sh
sed '1s/^64 192 256 1024$/64 202 256 1024/' ../../../tools/in/0000.txt > /tmp/ahc074-k202-0000.txt
g++ -std=c++20 -O2 -march=native -DLOCAL_BENCH -DPAPER_COUNT=202 src/esw-paper-count.cpp -o bin/esw-k202
bin/esw-k202 < /tmp/ahc074-k202-0000.txt > /tmp/ahc074-k202-0000.out
bin/replay-checker /tmp/ahc074-k202-0000.txt /tmp/ahc074-k202-0000.out
```

## 同じ100ケースの再計測

```sh
python3 scripts/reproduce.py --cases 100 --jobs 4
```

既定で、リポジトリの既存 `tools/in/0000.txt`〜`0099.txt` を読み、13水準のバイナリを元と同じ探索反復数・乱数種・コンパイルフラグでビルドして走らせます。独立チェッカーが全注文を確認し、結果を `results/reproduced_per_case.csv` と `results/reproduced_summary.csv` に出力します。全 stdout/stderr を別途保存する場合は `--store-outputs` を指定してください。追加の原実験の統計解析・描画などは添付ZIPのスクリプトを参照してください。

**注意:** 2秒制限で打ち切った実験ではありません。各ケースのCPU時間は測定機の負荷とハードウェアに依存し、今回の時間記録からジャッジへの提出可能性は保証できません。また、このランナーは原実験の完全な計測・集計スイートの代わりではなく、手数の主要比較と誤り0の再計測に絞っています。

## 統計の読み方

平均を102,400注文の独立標本として扱わず、同一seedのK=192との差を100組の対応差として集計しました。`summary.csv` は各比較の95%CIに加え、12比較のBonferroni同時区間も収録しています。192→193枚の1枚差は95%CIが0を含むため、有意と断定していません。詳しくは[レポート第3節](REPORT_ja.md)を参照してください。
