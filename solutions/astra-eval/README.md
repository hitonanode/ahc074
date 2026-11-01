# astra-eval（評価補助）

改良元: なし（提出用の解法ではない）。

Rust / Cargo が用意されていない実行環境でも、既存の `scripts/pahcer_run.py` に結果・出力・ソースを保存して同時比較するための補助。既存の `scripts/` と設定ファイルは変更しない。

- `tester.cpp`: `tools/src/lib.rs` と `tools/src/bin/tester.rs` の対話・可視性・移動・誤り判定を移植した POSIX C++23 テスター。**公式 Rust バイナリそのものではない。** 次の注文は直前の注文の処理完了後にのみ送る。出力全体を保存し、`scripts/observe.py verify` で独立した Python 再生とも照合する。
- `generate.py`: 問題の入力分布に従う Python 標準ライブラリの生成器。公式の ChaCha20 とは異なる乱数列なので、同じファイル番号でも公式 seed と同じ入力ではない。基準 seed は `0x4153545241303734`、各ケースの seed はこれにファイル番号を加えた値。各バーコードは64窓中32窓が黒で、256種の重複を拒否する。注文は1024回で連続同一商品を除く一様分布。
- `compare.py`: `scripts/pahcer_run.py` を import し、その `evaluate_compare` / `evaluate_extend` をそのまま呼ぶ。`--threads` で実行中の設定の並列数だけを変更する。コンパイルフラグ・ケースごとの順番交代・ロック・記録方法・統計量は既存と同一。単独解法の評価には対応しない。
- `smoke_test.py`: 既知の小ケース、不可視紙移動、不正入力、余分な出力、異常終了、次の注文の先読み防止をテスターと照合する。
- `prepare.py`: 元の公式入力を変更せず、新規ディレクトリへ評価に必要なソースと共通スクリプトをコピーし、独立した入力・実行記録を作る。保存済みバイナリをコピーせず、その環境でテスターをビルドする。

既存のリポジトリには公式の `tools/in/` があるので、再現時はまず別の場所を用意する。

```sh
python3 solutions/astra-eval/prepare.py /tmp/ahc074-astra-research --count 2000
cd /tmp/ahc074-astra-research
```

以下は、その独立ディレクトリ内で実行する。`prepare.py` を使った場合、コンパイルと入力生成は実行済みなので最初の2行と `generate.py` の行は省略できる。`smoke_test.py` はその環境で実行する。

```sh
mkdir -p tools/target/release
g++ -std=c++23 -O2 solutions/astra-eval/tester.cpp -o tools/target/release/tester
python3 solutions/astra-eval/smoke_test.py
python3 solutions/astra-eval/generate.py --count 2000
python3 solutions/astra-eval/compare.py --threads 2 --compare solutions/imp-gla solutions/<candidate> --seeds 0-64 --no-record -c "astra-generated-v1; C++ tester port"
python3 scripts/observe.py verify <run-id>
```

`generate.py` は既存ケースがあると既定では停止する。公式入力を上書きしないこと。生成ケースの SHA256 と seed は `generated_manifest.csv` に保存する。共有 `pahcer/` の履歴と公式 seed の best を混ぜないため、独自生成入力による比較では `--no-record` を付ける。結果は `runs/` に残る。

この環境の CPU とコンパイラはユーザーのローカル評価環境と異なる。時計依存の探索量と時間計測値は同一視できず、ここでの比較は同じ環境・同じ生成入力の paired comparison として扱う。

## 比較結果の書き出し

`export_results.py` は完了済みrunを読み、小さい `results/<run-id>.json`、`results/comparisons.csv`、`results/summary.json` を作る。指定したrunと同じ同時比較の全runを自動で含め、後日runを追加しても以前の書き出しを残す。原runは変更しない。

```sh
python3 solutions/astra-eval/export_results.py <run-id> [<run-id> ...]
```

スコアの正本は `result.json`、E/Tは独立再生の `metrics.json` とスコア式が一致するものを使う。ケース入力・評価時ソース・元記録のSHA256も保存する。stderr末尾に欠損がある場合もスコアを取り直さず、数値指標ごとの欠損件数と、Score行の有無を記録する。ソースの絶対パスや環境変数は書き出さない。実験条件は別のmanifestに残す。

固定設計の比較では、書き出し後に `analyze_controlled.py` で全体・事前保留範囲・探索的なモデル閾値サブグループを集計できる。基準stdoutの先頭192行と候補stderrの `initial_design_hash` をFNV-1a64で照合する。64bit hashは浮動小数点を経由せず整数として読み、JSONでは十進文字列にする。

```sh
python3 solutions/astra-eval/analyze_controlled.py <baseline-run> <candidate-run> --main-range 0-96 --holdout-range 32-96 --threshold -0.15
```

結果は `results/controlled_analysis.json`。範囲は終端を含まない。閾値サブグループは、強制採用モードの観測値を条件で抽出したものであり、通常採用モードを実行したスコアではない。

共用helperの3者同時比較は `analyze_shared.py` で、候補それぞれの基準に対する比較とshared対unionの直接比較を集計する。pilotとholdoutを別々に追記し、初期設計の一致・評価時ソースの固定・再利用数・穴数・モデル差分も検査する。新しい再生や解法実行はしない。

```sh
python3 solutions/astra-eval/analyze_shared.py <baseline-run> <union-run> <shared-run> --phase pilot
python3 solutions/astra-eval/analyze_shared.py <baseline-run> <union-run> <shared-run> --phase holdout
```

結果は `results/shared_analysis.json`。診断上のモデル差分と実測スコア差分は別の値として保存する。
