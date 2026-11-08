改良元: solutions/dcomp-t12-memo35（方策はdual25のslackを0.35へ拡大）

512byte-key whole-post memoに加え、Clangだけpostの可視性再生prefix cacheを無効化する。元の初期状態から同じ操作を再生するため、探索候補・計算値・出力・予算は変わらない。GCCは元のprefixを使い、両コンパイラで同じ通常6候補・第二親1個・共有6枠・3roundsを探索する。

時計による切替なし。F3_PREFIXで計測用の上書きを残す。ログ・trace・profiler・実験switch・段・DesignStoreを保持する。
