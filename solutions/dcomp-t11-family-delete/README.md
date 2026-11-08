改良元: solutions/dcomp-combo-alt1

raw計画をsame_familyでまとめる前に、単純削除を既存post_optimizeのdelete_onlyで行い、修復後の移動紙列・終状態・費用で候補を集める。計画生成側へは元の状態・操作列を返し、生成順を保つ。

設計は9候補のまま。予算は両コンパイラ共通の固定回数。既存ログ・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計による切替は使わない。
