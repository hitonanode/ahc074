# legal-mix-ej2-h3-exp6-pl2-nw5-slack35-pc4-ns3（注文処理の予算を変える版）

改良元: `solutions/legal-speed-fast`。`solutions/legal-notes/make_alloc.py` で作った。

## 改良元からの差分

- 最良の計画の取り出しの回数を 4 から 2 にする。
- 補助紙の計画の候補を 1 枚・2 枚とも 6 から 3 にする。
- 追加の候補の集め方 POST_CANDIDATES を 5 から 6 にする。
- 追加の候補の本探索の数 PLAN_LIMIT を 1 から 2 にする。
- 中立の書き換えの候補の数 NEUTRAL_WIDTH を 4 から 5 にする。
- 中立の書き換えの候補に入れる値の幅 NEUTRAL_SLACK を 0.25 から 0.35 にする。
- 編集する計画の数 kPostCandidates を 3 から 4 にする。
- 中立の書き換えの回数 NS_ROUNDS を 2 から 3 にする。

## 狙い

legal-speed-fast（legal-tie-fast と出力が同じで、注文処理が速い）で空いた時間を、時間あたりの得の大きい拡張に配り直す版（設計は変えない）。

- 削る 2 つ（取り出しの回数、補助紙の候補）は、設計固定の選別（solutions/legal-notes/PROGRESS.md の選別 A）で、時間あたりの損が注文処理の中で一番小さかった部分。
- 足す 6 つは、選別 E1・E2 で時間あたりの得が大きかったもの。
- 注文処理の時間を legal-tie-fast とほぼ同じにするように選んだ。指標は改良元と同じ。
