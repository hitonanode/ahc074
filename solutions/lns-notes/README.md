改良元: solutions/deval-helper-wide

Task 7 の設計側 LNS 研究の記録と再現スクリプト。注文処理は helper-wide に固定する。run.py は標準評価スクリプトを呼び、コンパイラにも共通 flock と nice を付ける。研究用の長時間実行は --no-record を付ける。

追加の研究メモは PROGRESS.md、実行方法は reproducibility.md にある。最終判定は REPORT.md にまとめ、phase 2 は開始しない。長い共通ロック待ちの間も、未完了の result.json は結果として使わない。
