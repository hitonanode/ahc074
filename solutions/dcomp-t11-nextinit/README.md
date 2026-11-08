改良元: solutions/dcomp-combo-alt1

next_costのprefix cacheが戻したrank/first/codeを直前に初期化しない。cache miss時だけ、実際に読むH列・2H色を初期化する。coveredとavailableも読む範囲だけ初期化する。計算項と加算順、候補順は同じ。

既存の固定予算、ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計による分岐は追加しない。
