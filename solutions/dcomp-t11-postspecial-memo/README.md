改良元: solutions/dcomp-t11-fast-nomemo

post_optimizeのMEMOをtemplate boolにし、呼出しの最初だけruntime設定で分岐する。大きな試行評価の内側で固定条件を繰り返し読む必要をなくす。両方の実験設定を残し、演算・候補順・探索回数を変えない。

GCCとClangで親に対するbyte一致と対応時間を測る。時計による切替なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。
