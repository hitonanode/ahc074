改良元: solutions/argon-des-perf-latew105

設計の評価関数の研究用（提出用ではない）。設計の段の固定の乱数の種を、環境変数で変えられるようにした。環境変数がなければ改良元と同じ出力になる。

- `DSEED_W`: 窓の割り当て（assign_windows）と比較器の初期化の種に足す値。
- `DSEED_A`: 焼きなまし（Design）、Hungarian による割り当て直し、穴あけの種に足す値。
- `DESIGN_SEED`: 上の 2 つのうち、指定のないものに使う値。
- 種は「元の種 XOR 値 × 0x9E3779B97F4A7C15」。値が 0 なら元の種のまま。
- 同じ値なら同じ設計になる（反復回数は固定）。`DSEED_A` だけを変えると、窓の割り当てと比較器は同じで、列・取っ手の焼きなまし以降だけが変わる。
- stderr の `dseed_w`・`dseed_a` に使った値を出す。
- 使い方の例: `DESIGN_SEED=3 scripts/pahcer_run.py solutions/deval-seed --seeds 0-1000 --save-design -c "DESIGN_SEED=3"`（解法は pahcer の環境を受け継ぐ）。
