# legal-roll3（legal-tie-fast を方策とし、次の注文の費用を内訳に分けた特徴も取る研究版。提出用ではない）

改良元: `solutions/legal-tie-fast`。main.cpp は `solutions/legal-roll/make_roll2.py --base solutions/legal-tie-fast/main.cpp` で作った。仕組みは solutions/legal-roll2/README.md と同じ（12 注文に 1 回、最大 5 候補、24 本 × 5 注文）。注文処理の出力は legal-tie-fast と同じ。

## legal-roll2 との違い

- `#rf` 行の最後に 3 列を足した: 次の注文の費用（adaptive_next_cost）のうち、1 手先の掘りの項、取っ手の色直しの項、残り（列 MDP の項）。補正をこの内訳で当てはめ直せるかを調べる。
