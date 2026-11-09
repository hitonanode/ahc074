改良元: solutions/ia-map-elites（solver本体はsolutions/dcomp-combo-dual30）

診断専用。窓探索が既に持つ別汎用窓集合のeliteをコピーして保存し、設計annealの共有前半が完成した直後に、現在の71ペアと列配置を移すと必要になる修復量だけを数える。修復、再初期化、再探索、候補選択変更は行わず、乱数とsolver状態は変えない。

保存するeliteは物理窓でのgeneric集合、極性、各窓の比較する紙ペア、目的値。現在の列handleもpermutationから物理窓へ戻す。新mapでもhandleである物理窓の列を維持し、失われた列を列番号の昇順、新handleを物理窓の昇順で対応させる。

各pairは原入力のバーコードと新eliteの比較器から6頂点DAGを構築して互換性を検査し、新handleで同色かも調べる。比較不整合pair、handle異色pair、handleを変えた列の全unitを解放対象と数える。解放対象の重複はunitごとにまとめる。pairの重みは2、singleは1なので、解放target数も重複しない。

`ia_map_repair_<指標>_<pool番号>` と、目的値最小の別集合1件の `<指標>_best` を出す。目的値同点ではpool内の最初。

- `gap` / `swaps`: 元の窓目的値との差、汎用/handle交換組数。
- `broken_generic` / `bad_handle`: 比較不整合pair数、新handleで異色のpair数。それぞれ独立に数えるため重複あり。
- `changed_columns`: handleを差し替えた列数。
- `released_units` / `released_targets`: 解放対象のunit数/商品数。
- `missing_columns` / `missing_colors`: 比較互換かつhandle同色のunitだけで仮配置した場合、どちらかの色がない列数/不足する色の数。
- `retained_missing_columns` / `retained_missing_colors`: 全解放対象を除いた残りで数える不足列/色数。handleを変えた列は必ず空なので、修復が埋める必要のあるanchorの数になる。
- `ia_map_repair_audited` / `ia_map_repair_best_pool`: 検査elite数と目的値最良のpool番号。検査なしなら0/-1。map再試行でGが変わり保存eliteと一致しなければそのeliteは検査しない。
- `@ia_map_repair`: 同じ値をpool番号、gap、swaps、broken_generic、bad_handle、changed_columns、released_units、released_targets、missing_columns、missing_colors、retained_missing_columns、retained_missing_colorsの順に出す。

通常compareで基準とstdout一致を先に確認する。これは修復の規模を測るprobeで、修復成功率や品質利得を実証するものではない。
