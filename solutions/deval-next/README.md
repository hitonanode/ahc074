# Task 4 実験スクリプト

改良元: solutions/deval-speed。基準はsolutions/deval-seven-wide。

標準pahcer_run.pyを呼ぶrun.pyと、出力一致・段別時間・seed単位の8列品質を集計するスクリプトを置く。設定選択はseed 0–499、最終の固定ソースは500–999で検証する。ビルド・重い分析は共有flock、評価は24並列。結果はこのディレクトリと新しいdeval-*解法にのみ保存する。

採用版の説明と全試行の結果は [deval-ordered8/REPORT.md](../deval-ordered8/REPORT.md) にまとめる。

`make_*.py`と`combine.py`が候補を生成する。`experiments.jsonl`が学習用の設計runと再評価runを対応付け、`summarize.py`と`report_tables.py`が一覧を作る。`freeze.json`は最終比較前のソースと時間条件だけによる選択規則、`final-runs.json`は最終runの対応表。`select_final.py`は通常比較の時間だけで選び、`final_metrics.py`が選択後の全指標を集計する。`render_report.py deval-ordered8`で報告書を再生成できる。

`build_submission.py`と`build_native.py`はGCC/Clangの提出用ビルドをflock内で行い、結果を解法ディレクトリのJSONへ保存する。ソルバーの評価は常に`run.py`経由の標準pahcerを使う。
