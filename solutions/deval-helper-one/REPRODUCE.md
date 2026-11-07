# 再現

作業ディレクトリはworktreeのroot。`main.cpp` は `FROZEN.json` のSHA256と一致する版を使い、F3・COLMDP・DSEEDなどの環境変数overrideは設定しない。`run.py` は標準 `scripts/pahcer_run.py` を呼び、コンパイルにも共有flockを付ける。評価は24並列、同時に一つだけ実行する。

最終の時間比較と通常スコア（元の判定時と同じ7解法）:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python solutions/deval-lastlab/run.py --compare solutions/argon-des-perf-latew105 solutions/deval-vbranch-nofb solutions/deval-flex125-plan3 solutions/deval-helper-fund solutions/deval-helper-gap1 solutions/deval-helper-wide solutions/deval-helper-one --seeds 0-2000 --save-design -c "Task6 frozen final reproduction"
```

採用案の固定設計による注文比較:

```sh
PYTHONDONTWRITEBYTECODE=1 /home/sato/ahc074/.venv/bin/python solutions/deval-lastlab/run.py --compare solutions/deval-flex125-plan3 solutions/deval-helper-one --design-from 20261107-165305_deval-flex125-plan3 --orders 4 --seeds 0-2000 -c "Task6 helper-one request reproduction"
```

採用根拠の保存runは `final-runs.json` にある。通常比較は `20261107-210226_*`、最終replayは `20261107-211724_*`。`final-metrics.json` はケース単位のSE、W/T/L、時間分布、未使用seedの集計を含む。`time-selection.json` はスコアを使う前に行った時間による選択の記録。`final_pair.py` はこの一回の凍結手続きを実施したもので、既存の `FROZEN.json` を上書きしない。

`../deval-lastlab/final_metrics.py` に `final-runs.json` のnormal/replay/extraを渡すと、元のresult.json、metrics.json、err/outから集計と注釈検査を再実行できる。重い集計は次の形で共有lockを取る。

```sh
flock -x /home/sato/ahc074/runs/.lock env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /home/sato/ahc074/.venv/bin/python solutions/deval-lastlab/final_metrics.py deval-helper-one --normal 20261107-210226_argon-des-perf-latew105 20261107-210226_deval-vbranch-nofb 20261107-210226_deval-flex125-plan3 20261107-210226_deval-helper-fund 20261107-210226_deval-helper-gap1 20261107-210226_deval-helper-wide 20261107-210226_deval-helper-one --replay 20261107-211724_deval-helper-one --request-reference 20261107-211724_deval-flex125-plan3
flock -x /home/sato/ahc074/runs/.lock env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 /home/sato/ahc074/.venv/bin/python solutions/deval-lastlab/finish_report.py deval-helper-one
```

GCC/Clang、C++23の提出用buildは `build_submission.py`、native版は `build_native.py`。これらは自身でflockを取り、binaryを実行せず、確認後に削除する。通常flagsでの出力一致は `../deval-lastlab/identity-extra.json` とREPORTの試行表に記録した。

指定されたjudge_model.pyとcmp_variant.pyは `../deval-lastlab/reference/` に内容を変更せず保存した。元のパスとSHA256は同ディレクトリのsources.jsonにある。再集計はscratchpadが削除された後もこのコピーを使う。
