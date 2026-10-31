# audit4-flip-clk

改良元: solutions/audit4-flip

時計の読みをすべて `CLOCK_SCALE` 倍するようにしただけで、探索の中身は同じ。

- 時間の測定はすべて `elapsed_sec()` を通るので、そこで経過時間に `CLOCK_SCALE` を掛ける。焼きなまし（1.1 秒で打ち切り）と山登り（1.15 秒で打ち切り）は、この倍率の掛かった時計で打ち切られる。
- `CLOCK_SCALE` はコンパイル時のマクロで、未定義なら 1.0（ジャッジ）。scripts/pahcer_run.py は `-DCLOCK_SCALE=1.1` でコンパイルするので、手元の 24 並列の評価では実時間の 1/1.1 で打ち切る。ジャッジは手元の 24 並列の評価の約 1.1 倍遅いので（trial_log.md の clock-probe）、手元とジャッジで探索量がそろう。
- stderr の `*_sec`（anneal_end_sec、end_sec など）も倍率の掛かった値で、ジャッジでの時間の見積りになる。
