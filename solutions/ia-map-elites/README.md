改良元: solutions/dcomp-combo-dual30

診断専用。窓割当ての最終選択後、既存の8枠elite poolに、選択したmapと異なる汎用窓集合が何個残っているかを読む。pool、返すmap、探索候補、乱数、反復数は変えない。第4枝への移植・再探索・修復は実装しない。

元の挿入箇所は `assign_windows` の `stats.gobj_after = cur`（dual30の2599行付近）、最終窓順へバーコードを変換する前。

- `ia_map_elite_total`: readyなelite数。
- `ia_map_elite_other`: 汎用窓集合が最終mapと異なるelite数。
- `ia_map_elite_min_gap`: それらの最小の窓目的値−最終map目的値。対象なしでは0。
- `ia_map_elite_best_swaps`: 目的値最小の別集合eliteとの、汎用/取っ手の交換窓組数。対称差のpopcount/2。目的値同点ではpool内の最初。
- `ia_map_elite_closest_swaps` / `mean_swaps`: 別集合eliteの交換組数の最小/平均。対象なしでは0。
- `@ia_map_elite <pool id> <目的値差> <交換組数>`: 別集合eliteそれぞれの診断行。

通常compareで基準とstdoutが同一であることを確認する。
