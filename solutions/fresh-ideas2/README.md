# fresh-ideas2

改良元: なし（解法ではなく、文脈を共有しない別 agent による「注文ごとの自由な選択を表示に変える仕組み」の検討の置き場所）

- paper_value.cpp: solutions/as6-cap38 の計測用コピー。`-DKK=191/192/193` で紙の総数 K を変え（専用紙 184 / 185 / 186 枚 = 対 72 / 71 / 70 組）、`-DSIM_HARNESS` と回数固定（MAP_ITERS=380000 GOPT_STEPS=110000 ANNEAL_ITERS=19000000 CLIMB_ITERS=65000）で SIM_SEQS=8 の模擬の手数を出す。補助紙の打ち切り（kHelperGiveUp）は外してある。紙 1 枚の限界の値段を測るためのもので、提出用ではない。
- run_sim.sh: seed の範囲を 4 並列で模擬する（`./run_sim.sh <binary> 100 164 res.txt`）。
- cmp.py: 模擬の結果どうしのケースごとの log 比の平均・標準誤差・勝/分/敗。
- gen_dist.py: 汎用紙 6 枚の 720 状態で、最下段を動かせない合法な手と、どの紙も動かせる手の平均距離（3.042 / 2.860）。
- res_pv191.txt, res_pv192.txt, res_pv193.txt: seed 100〜163 の模擬の結果。
