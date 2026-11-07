改良元: `solutions/deval-equalwide-fast`。

canonicalizeのK要素初期化を、現在の世代と旧fillerの印を一緒に保存するunsigned stampへ置き換える。世代のwrap時だけ配列を初期化する。候補の順・重複・旧filler優先順位を保つ。ejectの整数SIMDとcache keyの整数圧縮は改良元を引き継ぐ。設計の全予算・出力はflex125-plan3と同じ。注文だけの変更で、同generic移動数のhelperを見積り上位1件追加し、同距離goalは既存future優先で選ぶ。単独helper全体は上位6件、NS_ROUNDS=2、PLAN_SHORTLIST=3。

NEUTRAL_WIDTH=4。全予算は固定で、時間不足による切替えはない。DesignStoreは選んだ設計を保存し、@paper/@ops・全指標・trace・profiler・実験switch・段の目次を保つ。
