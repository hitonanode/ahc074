# deval-vanalysis

改良元: なし（評価関数 V の解析用。解法ではない）。

deval-vbranch-o3 が候補の選択に使う V16（`solutions/deval-model`、`solutions/deval-vbranch-o3/V.json`）の中身を調べる。

- `build_v16.py`: V16 と同じ設定（対象ごとの固定の digital shift、不一致数の解析的な積分）の特徴量を出す `features_v16` をビルドする（`flock` の下で実行）。
- `extract.py`: 特徴量を出す。
  - `restart7.npz`: seed 0〜999 × 設計 7 通り（deval-seed の作り直し）。
  - `branch4.npz`: seed 0〜499 × 分岐 4 本。deval-vtrain が各候補を強制したもの。
  - どちらも、注文の列 8 本での 1 注文あたりの手数を持つ。
- `vlib.py`: ケース内の中心化、ridge（Astra と同じ手順）、ケース内の相関と、選んだときの得。
- 解析の各段:
  - `a1_sanity.py`: 再現の確認。
  - `a2_redundancy.py`: 一定・重複の特徴。
  - `a3_blocks.py`: まとまりごとの寄与と除外。
  - `a4_minimal.py`: 少ない特徴量の V と前向き選択。
  - `a5_parts.py`: 取っ手の項のうちフィラーと色分布の更新の寄与、手の種類との対応。
  - `a6_branch.py`: 分岐 4 本での選択。
  - `a7_samples.py`: 積分点の数。

学習は seed 0〜499、成績は seed 500〜999（restart7）と、分岐 4 本の中での選択（branch4）で測る。結果は trial_log.md（2026-11-07 の V の解釈の節）。
