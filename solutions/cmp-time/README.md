# cmp-time

改良元: solutions/gpt6pro-06-01-comparator

gpt6pro-06 の設計の探索量を回数固定から時間制にし、余っていた時間を使う。

- 時計の倍率（CLAUDE.md）を入れた: 時計の読み（壁時計と、軽量処理に切り替える CPU 時間 1.55 秒の判定）をすべて `CLOCK_SCALE` 倍する（`scaled_seconds`、`scaled_cpu_seconds`）。
- 汎用窓の割り当ての山登り（optimize_map）: 2400 回（約 0.18 秒で上限）→ 時間制で 0.45 秒まで（温度は経過時間の割合で下げる）。汎用窓を減らす再試行は従来どおり 0.18 秒。
- 対・列の焼きなまし（PaperDesign::anneal）: 200 万回の上限 → 時間制で 1.10 秒まで。
- 動機: 元は平均 0.82 秒で終わっていた。注文を乱数で模擬して設計の期待手数を測ると（solutions/ceil-probe と同じ方法、seed 24〜87、32 本）、回数固定で割り当て 9600 回 −0.37%、焼きなまし 600 万回 −0.23% / 2000 万回 −0.60%、両方を増やす配分（4800 回 + 660 万回、9600 回 + 350 万回）はどれも −0.55% 前後。割り当ての目的の係数（generic_weight、strength、cutoff）は ±0.1% 以内で平ら。
- 実験用: 環境変数 `MAP_ITERS` / `ANNEAL_ITERS`（回数固定。設定すると時間の打ち切りもしない）、`MAP_SEED`（割り当ての乱数）、`MAP_GW` / `MAP_ST` / `MAP_CUT` / `MAP_WR`（割り当ての目的の係数 ×100）。`-DSIM_HARNESS` でコンパイルすると `SIM_SEQS=n` で乱数の注文列 n 本を模擬して平均手数を出して終わる。
- stderr に足したもの: `map_score`（割り当ての目的）、`gobj`（整合する対の貪欲マッチングのハンドル差。gsel の指標）、`compat_pairs`、`map_end_sec`、`init_end_sec`。
