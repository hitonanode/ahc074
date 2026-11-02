# astra-endval

改良元: `solutions/as6-cap38p0`。

ハンドルを複数同時に直す可能性を含む終状態価値を調べる研究ディレクトリ。現行計画器の合法な候補それぞれから仮想の次注文を実処理し、その平均手数と残存価値で選ぶ。実際の未来の注文は使わない。ここにある研究用C++は時間制約を外しており、そのまま提出する解法ではない。

基準との差分は以下。

- `research.cpp`: 設計の回数を固定し、元の計画候補と後処理済みの基準候補を収集する。現在の実手数と、次の実手数・終状態価値の平均との和で選ぶ。`ORACLE_SAMPLES=0` は基準と同じ方策、255は全次商品。終状態価値は元の `adaptive_next_cost + 0.6×残存穴埋め紙数`、係数 `TERMINAL_WEIGHT` の既定値は1。
- `diagnostic.cpp`: 1操作の差し込み先を、自分の列の全隙間・隣列の先頭3枚の前後へ広げる。旧D・旧穴埋め紙なら、浅い全列の境界と汎用層内も試す。実際の全操作を再生して合法性と表示を検査する。追加候補は `EXPAND_SCREEN` 個の仮想注文で `EXPAND_KEEP` 個へ絞る。本計測では8個で2候補へ絞り、元の候補と合わせ128商品で評価する。
- `fast.cpp`: 同じ計画を速く模擬するため、列内の紙順と紙の位置をキャッシュする。状態の復元時に無効化し、移動時は動いた列だけ更新する。価値の式・候補選択は変えない。
- `oracle.inc`, `harness.inc`, `expand.inc` と `build_*.py`: 研究用ソースを基準から再生成するための差分。
- `choice_audit.cpp`: 採用方策を変えず、異なる列の紙同士の前後関係が変わる候補・採用計画の数を記録する診断用ソース。

設計の固定回数は380000 / 110000 / 19000000 / 65000（順に `MAP_ITERS`, `GOPT_STEPS`, `ANNEAL_ITERS`, `CLIMB_ITERS`）。`SIM_SEQS=4`、1本1024注文。注文列と仮想注文の乱数は別々で、いずれも固定種。

`run_research.py` は指定seedの模擬を実行し、設計ごとのJSONLを `results/<label>/` へ保存する。`summarize.py` は4本を設計ごとに合算し、case log比の平均・標準誤差・勝分敗を計算する。`compare_identity.py` は高速化前後を時刻以外の全指標で照合する。`test_research.py` は公式テスターで1ケースずつ検査する。

JSONの `total` は実手数、`wrong` は誤表示、`illegal` は独立再生の違反数、`oracle_bad` は仮想次注文の誤表示数。`oracle_calls` は仮想注文の処理回数、`changed` は同じ開始状態の基準案と違う終状態を選んだ回数。内訳の分類と評価結果・採否は `REPORT.md` を参照。

再生成・再評価（各コマンドを順番に実行。既存の結果を再利用しない場合は新しいlabelを使う）:

```sh
python3 solutions/astra-endval/build_research.py
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 solutions/astra-endval/research.cpp -o solutions/astra-endval/research
python3 solutions/astra-endval/run_research.py --label baseline-repro --samples 0 --jobs 12
python3 solutions/astra-endval/run_research.py --label oracle255-repro --samples 255 --jobs 12
python3 solutions/astra-endval/build_diagnostic.py
python3 solutions/astra-endval/build_fast.py
g++ -std=c++23 -O2 -DCLOCK_SCALE=1.1 solutions/astra-endval/fast.cpp -o solutions/astra-endval/fast3
python3 solutions/astra-endval/run_research.py --binary fast3 --label expanded128-repro --samples 128 --jobs 13 --env EXPAND=1 EXPAND_SCREEN=8 EXPAND_KEEP=2
python3 solutions/astra-endval/summarize.py baseline-repro oracle255-repro expanded128-repro
```
