# if5-split-anneal（設計予算の配分の探り: 焼きなましを増やし、窓の割り当てを減らす）

改良元: `solutions/dcomp-combo-dual30`。

- 変更は反復回数の 2 定数だけ。kMapIters 450000 → 360000（−20%、Clang の段別時間で約 −65 ms）、kAnnealIters 11175000 → 13100000（+17%、約 +65 ms）。合計の設計時間はほぼ同じ。
- 目的: if5-split-map の逆向き。
