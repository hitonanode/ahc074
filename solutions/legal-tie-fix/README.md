# legal-tie-fix（ほぼ同点の最終選択の補正 + 2 回動かした紙をまとめる後処理）

改良元: `solutions/legal-tie-merge`（= `solutions/deval-helper-wide` + 2 回動かした紙をまとめる後処理）。設計は変えない。main.cpp は `solutions/legal-roll/make_tie_solver.py tie_w_gap03.json` で作った。

## 改良元からの差分

- **仕上がった計画を集める。** process() の中で、仕上がった計画を評価する箇所（後処理の後、eject の後、別の計画の後処理の後、中立探索の各候補の短縮の後、重み付きの計画）で、その終状態・手・plan_cost を記録する（終わりの重なり順ごとに plan_cost が最小のもの）。
- **最終の選択の補正（tie_choice）。** process() の最後に、記録した計画のうち plan_cost が選んだ計画との差 0.3 未満のものを、「plan_cost の差 + 終状態の特徴の差の一次式」で比べ直し、それが最も小さく 0 未満の計画に替える（再生で合法性・終状態・表示・補助紙の回収を確かめてから）。
  - 特徴: plan_cost の補助紙の項 fc、次の注文の費用 nc、汎用紙の項 gb、補助紙の数 nf、汎用層の下の補助紙の数 nfb、補助紙の担当する目標の数、列の先頭と逆の色の需要、手数。
  - 係数（生の単位）: fc +1.319、nc +0.190、gb +1.371、nf −0.628、nfb −0.101、補助紙の担当数 −0.044、逆の色の需要 −0.145、手数 −0.144、定数 −0.007。補助紙 1 枚の実際の費用は plan_cost の 0.7 手より約 0.3 手大きく、次の注文の費用は約 2 割、汎用紙の項は約 2.4 倍に効いている、という当てはめ。
  - 当てはめ: 設計固定の開ループ（solutions/legal-roll-feat、run 20261108-055819、16 注文に 1 回、SOTA の候補を 40 本 × 5 注文のロールアウトで測った）の seed 0〜99 のほぼ同点の代替への ridge 回帰（solutions/legal-roll/tie_fit.py --nolabels。検証と評価の結果は solutions/legal-notes/PROGRESS.md）。
- その後に legal-tie-merge の後処理（2 回動かした紙をまとめる）を行う。
- 時間不足の打ち切りなどはない。

## 指標（stderr）

- `tie_decisions`（記録した計画があった注文の数）、`tie_switches`（補正で選び直した回数）、`tie_rejected`（選び直しを再生の確認で取り消した回数）、`merge_trials` / `merge_saved`（legal-tie-merge と同じ）。
