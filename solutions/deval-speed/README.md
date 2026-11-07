# Task 3 の実験スクリプト

改良元: solutions/deval-vbranch-o3。高速化、出力一致、時間の再配分を調べる再現用スクリプト。ソルバー本体は各 deval-* ディレクトリに置く。

- `run.py`: 標準 `scripts/pahcer_run.py` を呼ぶ。ビルドだけにも共有flockを追加する。`DEVAL_CXX=clang++` でClangを選べる。
- `DEVAL_BUILD_REUSE=1`（既定、0で無効）: 完了したrunに、ソースSHA-256・コンパイラの版・全コンパイルフラグが一致する単一ファイルのビルドがあれば再利用する。再利用元はrunの`compile.log`に記録する。評価自体の保存・ロック・記録は標準スクリプトのまま。
- `experiment.py TAG SOLUTION=solutions/NAME [SEEDS=0-500] [DESIGN_FROM=RUN]`: 通常の設計保存と8列リプレイを順に実行し、`experiments.jsonl`へ追記する。
- `compare_runs.py REF CAND OUTPUT.json`: 同時比較の出力ファイル一致、候補数、段別時間差と標準誤差、judge時間を集計する。
- `analyze_quality.py REF CAND... --seeds 0-500 --output OUTPUT.json`: seed単位で注文列をまとめ、log比の平均・標準誤差を出す。
- `make_*.py`: 各試行のソースと日本語READMEを生成する。既存の基準解法は編集しない。
- `audit_final.py SOLUTION NORMAL REPLAY`: ソースサイズ・保存ソースとの一致・目次・無効スコア・通常評価とリプレイの実列一致を検査する。

分析と単体テストは共有flock下で実行する。設定選択はseed 0–499、最終設計リプレイは500–999。結果の負号が改善。設計リプレイは各seedで対象の注文列のスコアを算術平均してからlog比を取る。±はseed間の標準誤差。

最終版は `solutions/deval-seven-wide/`。最終比較と未使用seedの評価は`final_evaluate.py`、集計は`summarize_final.py`、提出ビルドは`build_final.py`、日本語報告書の組立ては`write_report.py`。最終設定の選択根拠は同ディレクトリの`SELECTION.md`、固定したソースは`FROZEN.json`で確認できる。
