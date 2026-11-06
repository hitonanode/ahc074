# deval-v3refine

改良元: `solutions/deval-vbranch-nofb`。研究用（提出用ではない）。

V を目的関数として直接下げると、本当の手数も下がるか（V が因果的か）を確かめる版。V で 4 候補から選んだ後の設計に、`solutions/deval-vselect` と同じ「2 枚の紙の担当（1 対象か 2 対象の組）を入れ替える」手を `DEVAL_REFINE` 回試し、目的関数が下がる手を採る。各紙の穴あけと、各列の両方の色は保つ。

- `DEVAL_REFINE_MODEL=3`（既定）: V3 = 0.930 col + 1.032 gc + 0.877 m_s2_it2_cost（列の掘り出し・汎用紙・被覆 DP の取っ手の費用。restart 設計の seed 0〜499 で学習した 3 項の形）。
- `DEVAL_REFINE_MODEL=5`: 取っ手の費用を fix / fill / fdig に分けた 5 項の形。
- `DEVAL_REFINE_MODEL=16`: 選択に使う V16 そのもの。
- `DEVAL_REFINE_LIMIT`: 改善を打ち切る設計の経過秒（既定は打ち切らない）。

`DEVAL_REFINE` を指定しなければ deval-vbranch-nofb と同じ出力。stderr の `dv_refine_accepted` は採った手の数、`dv_refine_v16_before/after` と `dv_refine_v3_before/after` は改善の前後の V16 と V3、`dv_refine_sec` はその時間。

`DEVAL_PRECLIMB` は、各候補の焼きなましの直後・仕上げの前に、2 つの紙（unit）の列を入れ替えるか 1 つの紙を近くの列へ動かす手を指定回数試し、穴あけ前の自然な紙（`finish(raw)`）で測った目的関数（`DEVAL_REFINE_MODEL`、既定 V3）が下がる手を採る。採った後に設計の集計を作り直し、通常どおり仕上げる。stderr の `dv_preclimb_tried` / `dv_preclimb_accepted` / `dv_preclimb_before` / `dv_preclimb_after` / `dv_preclimb_sec`。

`DEVAL_PRECLIMB_HANDLES=1` のときは、仕上げ前の climb の手を「2 つの深さの取っ手の窓を交換する」だけにする（全対象の 2 つの色のビットが入れ替わる。対の紙が自分の列の取っ手で色が揃い、各列に両方の色が残る場合だけ試す）。多くの対象の費用が一度に変わる手なので、V3 の誤差が打ち消し合うかを確かめる。

対照の `DEVAL_PRECLIMB_RANDOM=k`: 評価せずに、最初の k 個の合法な手をそのまま採る（V3 で選んだ手とランダムな手の差を測るため）。

対照の `DEVAL_REFINE_RANDOM=k`: 仕上げ後の入れ替えを評価せずに、最初の k 個の合法な入れ替えをそのまま採る。

`DEVAL_REFINE_MOVE=1` のときは、仕上げ後の改善の手を「2 枚の紙の間で対象を 1 つずつ交換する（対の組み替え）」にする。新しい対は汎用紙の層で両立し、紙の列の取っ手で色が揃う場合だけで、各列に両方の色が残り、各紙の穴あけは保つ。仕上げの段は対を変えないので、仕上げが最適化していない手を V で選べるかを確かめる。
