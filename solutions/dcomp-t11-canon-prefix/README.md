改良元: solutions/dcomp-combo-alt1

canonicalizeのbottom-up scanを8紙ずつの整数prefix minimumへ置換する。generic紙を負の値、capをHとして扱うと、minより大きい列の紙だけが元のout-of-column紙になる。nonemptyはminが初めてその列へ下がる時だけ記録する。out紙の順序と後半の正規化は元のまま。

profileのcanonicalize段を対象とする。浮動小数・候補順・予算は変えない。両コンパイラでbyte一致を測る。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。時計分岐なし。
