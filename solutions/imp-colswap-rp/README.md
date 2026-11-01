# imp-colswap-rp

改良元: solutions/imp-colswap

imp-colswap の「対の組み替え」（対 (a, b) + 単独 c, d → 対 (c, d) + 単独 a, b。新しい対は 3 列のうち自分のハンドルで一致する列から乱数で選ぶ）を有効にした版。違いは REPLACE_RATE の既定値だけ（0 → 100、つまり焼きなましの手の 10%）。その分は整合する相手への目標の交換から取る（cmp-anneal で 230‰、imp-colswap で 210‰ → 110‰）。

- 対の組み替えは solutions/gpt6pro-07-02-replace の pair replace（列の修正つき、手の 10%）と同じ形。gpt6pro-06-02-regroup の pair shift（新しい対が単独 c の列に入る）は、この結果の 1 つ。
- 手の中身・評価（Annealer::multi_move）と stderr の `replace_tried` / `replace_accepted` は imp-colswap の README を参照。

パラメータ: COLSWAP_RATE = 20、COLSWAP_DIST = 4、REPLACE_RATE = 100、REPLACE_REPAIR = 1（ほかは imp-colswap と同じ）。
