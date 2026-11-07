改良元: `solutions/deval-next` の実験用スクリプト。基準解法は `solutions/deval-ordered8`。

Task 5の生成・評価・集計を置く。標準pahcer_run.pyを呼び、ビルドと重い分析は共有flock内で行う。設定はseed 0–499、最後の固定ソースは500–999と通常2000件で評価する。全予算固定、時間不足による切り替えを加えない。

最終解法と結果は `../deval-flex125-plan3/REPORT.md`。各試行の定義は `TRIAL_GUIDE.md`、全数値は `TABLES.md`、run対応は `experiments.jsonl` と各評価ログにある。

記録付きの最終比較を再実行するコマンド（作業ディレクトリはこのworktreeのルート）:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python solutions/deval-pipeline/run.py --compare solutions/argon-des-perf-latew105 solutions/deval-vbranch-nofb solutions/deval-ordered8 solutions/deval-flex125-plan3 solutions/deval-flex125 solutions/deval-flex8-fast --seeds 0-2000 --save-design -c "Task5 frozen final reproduction"
```

保存済みの最終設計で未使用500ケースの8列を再実行する場合:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python solutions/deval-pipeline/run.py solutions/deval-flex125-plan3 --design-from 20261107-165305_deval-flex125-plan3 --orders 8 --seeds 500-1000 -c "Task5 held-out reproduction"
```

`run.py` は標準評価スクリプトをimportして呼ぶ。標準の評価ロックに加え、コンパイラも同じflockで保護する。同一ソース・同一コンパイラ・同一フラグの既存バイナリだけを再利用できる。Clangでの同一出力検査は `DEVAL_CXX=clang++` を付ける。解法を直接実行しない。

`final_pair.py` は新しい解法ディレクトリに対し、ソースと採用順を固定してから通常比較・時間条件での選択・1案だけの未使用replayを実行する。既存の `FROZEN.json` を上書きしない。過去の結果の再集計は `final_metrics.py` に `final-runs.json` のrun-idを渡す。

分析の再生成:

```sh
flock -x /home/sato/ahc074/runs/.lock env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /home/sato/ahc074/.venv/bin/python solutions/deval-pipeline/summarize.py
PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python solutions/deval-pipeline/tables.py
PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python solutions/deval-pipeline/report.py deval-flex125-plan3
```

提出用ビルドの確認は `build_submission.py` と `build_native.py` に解法名を渡す。GCC/Clangを内部でflockし、バイナリを実行せずに削除して、コマンド・ソースハッシュ・成否を解法ディレクトリへ保存する。
