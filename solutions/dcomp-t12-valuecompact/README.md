改良元: solutions/dcomp-combo-dual25

next_costのcache entryを詰め、sizeとvalueをkeyより前へ置く。in-placeとfillerが排他的なのでkeyは最大2K+1 byteで、2K+8 byteの領域で足りる。key生成用の一時領域は元のまま。

完全キーを比較するexact cacheだけの変更。計算順・探索・出力を変えない。CLOCK_SCALE・ログ・実験switch・段・DesignStoreを保持する。
