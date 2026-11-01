# night-probe4

改良元: solutions/astra-search

計測用（模擬 -DSIM_HARNESS で使う）。環境変数 `NP_NOHG=1` で補助紙の表の打ち切り（倍率込み 1.55 秒）をなくすだけ。既定では astra-search と同じ。
- `NP_HDW`: 窓の割り当ての目的関数で、対のハンドル窓の違い 1 つの重み（1/3600 手、既定 2340）
- `NP_RELW` / `NP_FULLW`: 同じ目的関数の両側の汎用層の値の重み（既定 5）/ 全窓の違いの重み（既定 144）
