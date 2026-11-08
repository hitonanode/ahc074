改良元: solutions/dcomp-t12-postmemo

whole-post memoのkey bufferを2336から512 bytesへ縮め、32entryの常用部分をcacheへ収めやすくする。64操作または32 fillerを超える入力はキャッシュを使わず元の同一処理を実行する。最大key489 bytesのため切捨てや衝突共有はない。探索結果・探索回数は変えず、時計で切り替えない。ログ・trace・profiler・実験switch・段・DesignStoreを保持する。
