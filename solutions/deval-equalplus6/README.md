改良元: `solutions/deval-helpeq1`。

NEUTRAL_WIDTHを4、NS_ROUNDSを3にし、PLAN_SHORTLIST=5で1手長い候補まで後処理する。設計は同じ。

単独helperの同generic距離候補を見積り上位1件まで追加し、最少generic距離のgoalは既存futureの低い方を選ぶ。元のgeneric移動を減らすhelperは残し、合計上位6候補とする。時計による切替えはない。元のログ・注釈・実験スイッチを保つ。
