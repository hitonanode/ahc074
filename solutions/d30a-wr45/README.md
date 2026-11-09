改良元: solutions/dcomp-combo-dual30

窓割り当ての役割交換の提案割合 kWindowRate を 0.6 から 0.45 に下げる。安い transfer 提案の割合を増やし、同じ時間で多く探索する狙い。既定 MAP_ITERS は 450000 から 490000 に増やす（提案段階の時間測定から約 9% を戻す）。gopt と後続の設計・注文処理は変更しない。

LOCAL_BENCH の D30A_WINDOW_RATE で提案割合、既存の MAP_ITERS で固定反復数を指定できる。元の設定は D30A_WINDOW_RATE=0.6、MAP_ITERS=450000。新しい stderr 指標はない。gobj_after、map_end_sec、dv_best とスコアで効果を見る。

固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。新しい stderr 指標はない。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。
