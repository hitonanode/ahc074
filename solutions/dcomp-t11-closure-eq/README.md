改良元: solutions/dcomp-combo-alt1

窓割当で、旧互換ペアの変更後の辺集合が「旧DAGの推移的簡約以上、旧閉包以下」なら閉包は同じである。この場合だけ旧費用を再利用する。閉包と簡約は旧raw relation完全一致をkeyとして記憶する。ペアの列挙順・matchingの同点順は保つ。

closure_reusedは省略数、closure_equiv_builtはcache作成数。両コンパイラの探索予算・既存ログ・profiler・実験スイッチ・目次と段・DesignStoreは保持。時計による切替はない。
