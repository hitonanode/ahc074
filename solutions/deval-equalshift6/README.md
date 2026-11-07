改良元: `solutions/deval-helpeq1`。

最初の4枝の穴あけ前rematchを2回から1回へ減らし、浮いた時間をNEUTRAL_WIDTH=4とPLAN_SHORTLIST=5（1手長い候補も後処理）へ回す。NS_ROUNDS=2を維持する。完成8候補・焼きなまし・窓割当ては同じ。

単独helperの同generic距離候補を見積り上位1件まで追加し、最少generic距離のgoalは既存futureの低い方を選ぶ。元のgeneric移動を減らすhelperは残し、合計上位6候補とする。時計による切替えはない。元のログ・注釈・実験スイッチを保つ。
