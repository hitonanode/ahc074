# night-probe5

改良元: solutions/imp-s2hd

計測用（模擬 -DSIM_HARNESS で使う）。環境変数 `NP_NOHG=1` で補助紙の表の打ち切り（倍率込み 1.55 秒）をなくすだけ。既定では imp-s2hd と同じ。
- `NP_CUT`: 窓の割り当てで数える近い対の距離の上限（既定 26）
