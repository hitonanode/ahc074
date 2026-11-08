改良元: solutions/dcomp-combo-dual25

next_costのexact value cacheを256から1024 slotへ拡大し、修復候補間の追い出しを減らす。キーとdouble値は元のまま。

完全キーを比較するexact cacheだけの変更。計算順・探索・出力を変えない。CLOCK_SCALE・ログ・実験switch・段・DesignStoreを保持する。
