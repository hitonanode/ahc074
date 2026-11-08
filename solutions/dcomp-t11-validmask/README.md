改良元: solutions/dcomp-combo-alt1

Clangのdense valid列挙でnrel配列を再度load・比較する代わりに、SIMD更新時点で得た8laneのcompatible maskを保存する。新しくacyclicと判定されたpairだけbitを加え、元と同じ順で圧縮する。GCCは既存の疎な経路を保つ。

探索予算・候補順・lookup順・算術は変更しない。両コンパイラで同じ予算を使用する。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。
