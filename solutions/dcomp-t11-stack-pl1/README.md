改良元: solutions/dcomp-combo-alt1

出力同一の要求高速化（anchor配列・遅延anchorize、部分MDP cache、next_cost初期化省略、end-memoの4本hash）を基礎にする。探索の変更は、raw候補の二重移動結合をfamily選別の前に行うこと、joint filler DPの同点で広い区間を選ぶこと、完成ALT計画をもう一つ中立探索の親にして1→1だけ列挙すること。追加親はgap .3以内で最大1個、元の6候補枠を共用する。

通常post候補数は6、expandedの本修復枠は1。それ以外の予算・9設計候補は親のまま。両コンパイラで同じ設定を使い、時計による切替なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。
