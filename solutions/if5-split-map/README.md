# if5-split-map（設計予算の配分の探り: 窓の割り当てを増やし、焼きなましを減らす）

改良元: `solutions/dcomp-combo-dual30`。

- 変更は反復回数の 2 定数だけ。kMapIters 450000 → 560000（+24%、Clang の段別時間で約 +79 ms）、kAnnealIters 11175000 → 8800000（−21%、約 −79 ms）。合計の設計時間はほぼ同じ。
- 目的: 最終版（時間で決める設計）の段の配分を変える価値を、gobj_after・dv_best と通常のスコアで探る。
