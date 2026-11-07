改良元: `solutions/deval-helpeq1`。

helper候補の事前順位にも既存のgeneric末端価値future×0.5を加える。

同generic距離の追加helperは上位1件、通常候補と合計6件のまま。実行した候補は従来通り実際のplan_costと合法性で評価する。設計と探索予算は固定し、時計による切替えはない。
