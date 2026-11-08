改良元: solutions/dcomp-combo-alt1

window evaluate_moveの8lane方向flag展開を dircompact へ変更する出力同一の試験。元の32bit×8表に対し、8bit×8表のzero extend、PDEPで各byteへ散布してzero extend、定数bitとのSIMD比較のいずれかを使う。lane値は元の0/1と完全に同じ。

profileでmapの約24%を占めたSIMD段の表容量・依存関係を短縮する。固定予算・候補順・計算式・ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。
