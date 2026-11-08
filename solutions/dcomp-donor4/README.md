改良元: solutions/dcomp-screen-replay

rematchのdonor評価で、4 targetの修復可能handle集合だけをAVX2で同時計算する。不一致の最上位bit以下をOR/shiftで塗り、従来のlevel cutoffと同じ集合を作る。確率多項式とsumは元のtarget順・演算のまま。探索、乱数、浮動小数点、候補数、ログ・実験スイッチを維持。
