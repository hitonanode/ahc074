# deval-v3refine

改良元: `solutions/deval-vbranch-nofb`。研究用（提出用ではない）。

V を目的関数として直接下げると、本当の手数も下がるか（V が因果的か）を確かめる版。V で 4 候補から選んだ後の設計に、`solutions/deval-vselect` と同じ「2 枚の紙の担当（1 対象か 2 対象の組）を入れ替える」手を `DEVAL_REFINE` 回試し、目的関数が下がる手を採る。各紙の穴あけと、各列の両方の色は保つ。

- `DEVAL_REFINE_MODEL=3`（既定）: V3 = 0.930 col + 1.032 gc + 0.877 m_s2_it2_cost（列の掘り出し・汎用紙・被覆 DP の取っ手の費用。restart 設計の seed 0〜499 で学習した 3 項の形）。
- `DEVAL_REFINE_MODEL=5`: 取っ手の費用を fix / fill / fdig に分けた 5 項の形。
- `DEVAL_REFINE_MODEL=16`: 選択に使う V16 そのもの。
- `DEVAL_REFINE_LIMIT`: 改善を打ち切る設計の経過秒（既定は打ち切らない）。

`DEVAL_REFINE` を指定しなければ deval-vbranch-nofb と同じ出力。stderr の `dv_refine_accepted` は採った手の数、`dv_refine_v16_before/after` と `dv_refine_v3_before/after` は改善の前後の V16 と V3、`dv_refine_sec` はその時間。
