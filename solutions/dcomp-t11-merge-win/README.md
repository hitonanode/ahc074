改良元: solutions/dcomp-combo-alt1

post_optimizeの合法候補に対し、二重移動の同終状態への結合を費用比較の前に行う。適用条件: value < best_score+1e-8。候補の終状態・将来費用は同じで、操作数だけ正確に減る。prefixの再生記録は修復前のまま保持する。

修復は同じ終状態に到達する合法な操作列への短縮だけ。固定予算を両コンパイラで共用し、時刻による切替なし。既存ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。
