# night-probe

改良元: solutions/imp-gla

計測用（模擬 -DSIM_HARNESS で使う）。係数を環境変数で変えられるようにしただけで、既定値では imp-gla と同じ。

- `NP_GC`: 設計の対の汎用層の費用 gc の倍率 ×100（既定 100）
- `NP_TP`: kTopPenalty ×100（既定 35）、`NP_EW`: kEndWeight ×100（既定 100）、`NP_FC`: kFillerCharge ×100（既定 60）
- `NP_NOHG`: 1 なら補助紙の表の打ち切り（倍率込み 1.55 秒）をなくす（回数を固定して設計を長く回す実験で、補助紙が消えないように）
