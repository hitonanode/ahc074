# [NOT FOR MERGE] 2→2中立リライト＋再短縮の研究資料

既存の提出用ソルバを変更せず、ChatGPTとの検討で得た注文処理の改善を記録する。詳しいアルゴリズム・数式・14→14→11の説明は、この資料を追加したDraft PRの本文に記載している。

**研究用。2秒制限への適合は未確認であり、記録した全量版のローカル時間は平均3.671秒、最大4.191秒。提出用としてそのまま採用しない。**

## 基準と記録の由来

基準は `solutions/eject-single-window/main.cpp`。PR作成時のmain `bde7523bab7fa158c12b744f6ab417d00014ce84` 上のこのファイルは、会話に提供されたコードとGit blob単位で一致した。

- 基準blob: `8136e2455cc70038e3f7993ac1e7979d3ed2767f`
- 基準SHA-256: `5f58f1c24f8a643c589124bad0b93d29c35d029a2c7d6ca9f2964726ff7b4bdd`
- 固定作業量の研究ソースSHA-256: `ffe3afdb636114b52eeaf4bf5ed399d95ebdb2c5e63e45d2a4cdb62ff58e9df1`
- 元資料: 会話添付の `ahc074_neutral_escape_experiments.zip`
- 元資料SHA-256: `85b1844f3c29e4f1c03fffa12f5a068f1a50f7be251db8a4d74f57c9adb36e84`

現行mainにある他の改良系統を基準にした比較ではない。過去の固定反復実験を移管したもので、リポジトリのpahcer run-idはない。pahcerの公式評価記録へ混ぜていない。

## 収録物

| ファイル | 内容 |
|---|---|
| `neutral-escape-core.patch` | 基準コードへの機能差分。元の時計と軽量モード切替を維持する |
| `prepare.py` | 基準のハッシュを確認し、別ディレクトリへ対照・候補C++を復元する |
| `verify.py` | 全操作の可視性・最終表示の独立検証、およびtraceからの具体例の抽出・再検証 |
| `results.csv` | 保存済み80実行のケース別手数・誤り・時間 |
| `verification.json` | PR作成時に元資料の80出力を再生した検証結果 |

全出力・全ログ・以前の3→2ソース・4注文に1回版などの探索用派生ソースは元の会話添付ZIPにある。このPRには大量の出力を重複してコミットせず、主要方式を復元するパッチと検証用スクリプトを収録した。

## 結果の要点

| 方式 | ケース数 | 平均手数/注文 | 対照からの削減 | 勝/分/敗 |
|---|---:|---:|---:|---|
| 対照 | 20 | 10.22666015625 | — | — |
| 前回3→2共同修復 | 20 | 10.21953125 | 146手 | 15/2/3 |
| 2→2中立リライト＋再短縮 | 20 | 10.186181640625 | 829手 | 20/0/0 |

新方式の平均削減は0.040478515625手/注文、総手数比で0.395813638%改善。seedごとの `100*log(候補/対照)` の平均は−0.397151%、標準誤差は0.057193パーセントポイント（20 seed）。これは固定設計・固定反復の20ケースにおける記述統計で、全2000ケースや2秒制約下への保証ではない。

seed 0000–0009では380手、手法固定後の追加確認0010–0019では449手減った。印刷された192枚は対照と全20ケースで同一。誤り・不可視操作ともに0。

## 具体例を再現する

以下は過去実験の再現専用であり、通常の提出用評価ではない。Linux、Python 3.10以降、`patch`、C++23対応のg++、AVX2等を利用できるCPUを使う。リポジトリルートから実行する。出力先は存在しないディレクトリを指定する。

```sh
python3 docs/chatgpt-neutral-escape/prepare.py \
  --out /tmp/ahc074-neutral-repro --fixed-work

g++ -O2 -std=c++23 -march=native \
  /tmp/ahc074-neutral-repro/neutral_escape.cpp \
  -o /tmp/ahc074-neutral-repro/neutral_escape

env BENCH_FIXED=1 MAP_ITERS=160000 GOPT_STEPS=60000 \
  ANNEAL_ITERS=10000000 CLIMB_ITERS=16000 \
  NEUTRAL_DEPTH=2 NEUTRAL_WIDTH=4 NEUTRAL_SIGNATURE=0 TRACE_MAGIC=1 \
  /tmp/ahc074-neutral-repro/neutral_escape \
  < tools/in/0000.txt \
  > /tmp/ahc074-neutral-repro/neutral_full_0.out \
  2> /tmp/ahc074-neutral-repro/neutral_full_0.log

python3 docs/chatgpt-neutral-escape/verify.py \
  tools/in/0000.txt /tmp/ahc074-neutral-repro/neutral_full_0.out \
  --trace /tmp/ahc074-neutral-repro/neutral_full_0.log \
  --export-witness /tmp/ahc074-neutral-repro/witness.json
```

期待値は1024注文、10423手、誤り0、不可視操作0。その後、`before=14`、`neutral=14`、`after=11`、`simple_after=11` の合法性・正表示と、次の削除関係を検証する。

- 42だけ削除: 合法・正表示。
- 42と82を削除: 48への操作が不可視になり不正。
- 42と48を削除: 合法だが窓26が誤表示。
- 42・82・48を同時削除: 合法・正表示。

紙117が11窓を担当し、残した紙82が窓26を担当することも検査する。エクスポートしたJSONには全192枚の模様、開始積層、全操作の数値挿入位置を含む。

PR作成時、この復元ソースをC++23でコンパイルし、seed 0の出力が保存済み出力とバイト単位で一致することを確認した。上記検証器による具体例の再検証も成功した。

`--fixed-work` は外側の `elapsed_sec()` を `BENCH_FIXED` 指定時に0へ固定し、注文途中の軽量モードを無効化する。4種類の反復回数は必ず明示する。ソルバ自身は未来の注文を読まず、1注文ずつ処理する。標準入力リダイレクトは過去記録の再現であって、公式reactiveテスターの実行ではない。

`prepare.py` の `--fixed-work` を省くと時計・軽量モード切替を維持した機能差分版を生成する。ただし追加探索で切替が早まり、総手数が悪化する可能性がある。提出適合を意味しない。

元の研究ソースは環境変数未指定時の設定が小さいため、復元版でも `NEUTRAL_DEPTH=2`、`NEUTRAL_WIDTH=4` を明示する。機能差分パッチのみの版は未指定時を2/4にしてある。

## 検証範囲と次の作業

このPRの時間表は保存済み実験の壁時計時間であり、今回の再測定やAtCoder実測ではない。以前の3→2の秒数は別の実験時点なので、今回の秒数との差を厳密な速度差として扱わない。

本採用の前には現行の注文処理へ別ディレクトリで移植し、リポジトリ標準の設計固定比較と通常の2000ケース比較、時間分布を確認する必要がある。今回のPRはその実装・採用を行わない。10.0手以下および2–3%改善は未達。
