改良元: solutions/deval-pipeline の分析スクリプト。Task 6の実験用。基準はdeval-flex125-plan3。設定選択はseed 0–499、最後は凍結したソースを未使用seedと通常2000件で検証する。評価は標準pahcer_run.pyを経由し、ビルド・重い分析は共通flock下で行う。


最終検証は `final_pair.py`。学習結果から候補の優先順とソースhashを固定し、argon / nofb / flex125-plan3を同じ通常2000件のcompareへ入れる。平均時間比とp99だけで候補を一つ選び、その後だけ未使用seedのreplayを行う。各candidate自体の予算は固定で、実行中にfallbackしない。`final_metrics.py` は平均・SE・W/T/L・時間分布・ソースと操作ラベルを検査する。

`last_checks.py` / `combined_checks.py` は両compilerでの出力同一検証と、flock付き提出buildを行う。`source_audit.py` は容量・段・時計と未使用関数削除の確認。`refresh_report_data.py` / `render_extra.py` / `write_report.py` で学習表と最終REPORTを生成する。再集計にも共通lockを使う。分析の主要な状態とrun-idは、このディレクトリ内のSTATE.md、JSONL manifest、各評価logへ記録する。
