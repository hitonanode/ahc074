# imp9-both

改良元: solutions/imp9-assign

solutions/imp9-assign（窓の割り当てを 70 対の費用で評価）に、solutions/imp9-sym（設計の対の汎用層の費用を 2 目標の両側の平均にする）を合わせたもの。

- 両側の平均は、imp9-sym のように mean_moves を 2 回呼ぶ代わりに、imp9-assign の半順序の表（PosetSums::both_of / 1440。値は mean_moves の 2 回の平均と同じ）から引く。表引きは mean_moves の計算より速く、Design::initialize が約 0.015 秒短くなる（その分、設計の焼きなましが長くなる）。
- これで、割り当ての評価（70 対の費用）と Design::initialize の対の選び方（0.65 × ハンドルの違い + 2 gcost + 0.04 × 違い）が同じ費用の形になる（割り当ては距離 26 以下の対だけを見る点だけが違う）。

stderr は imp9-assign と同じ。
