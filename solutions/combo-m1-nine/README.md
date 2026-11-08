# combo-m1-nine（M1 の注文処理 + dcomp-nine の設計）

改良元: `solutions/legal-tie-fast`。2 つの親の変更を 3 方向でまとめた（`git merge-file`。衝突なし。ほかの変更はしていない）。

- 注文処理の親: `solutions/legal-mix-ej2-h3-exp6-pl2-nw5-slack35-pc4-ns3`（M1）
- 設計の親: `solutions/dcomp-nine`

main.cpp は、legal-tie-fast からの M1 の差分（注文処理の部分と統計の行）と dcomp-nine の差分（設計の部分）を両方そのまま持つ。2 つは触る行が重ならない。

## legal-tie-fast からの差分

注文処理（M1 から。設計の段には影響しない）:

- 後処理の差し込み先の付け替え（古い補助紙・2 回動かす紙）と、削除と付け替えの組で、試行の最後の表示を、手 i（と j）を除いた並びから見積もる（solutions/legal-speed-fast）。表示が A_u にならない試行は evaluate を呼ばずに飛ばす。後の手と入れ替えられる場合だけで、出力は変わらない。指標 `screen_prepared`・`screen_skipped`。
- 最良の計画の取り出しの回数を 4 から 2 にする（ej2）。
- 補助紙の計画の候補を 1 枚・2 枚とも 6 から 3 にする（h3）。
- 追加の候補の集め方 POST_CANDIDATES を 5 から 6 にする（exp6）。
- 追加の候補の本探索の数 PLAN_LIMIT を 1 から 2 にする（pl2）。
- 中立の書き換えの候補の数 NEUTRAL_WIDTH を 4 から 5 にする（nw5）。
- 中立の書き換えの候補に入れる値の幅 NEUTRAL_SLACK を 0.25 から 0.35 にする（slack35）。
- 編集する計画の数 kPostCandidates を 3 から 4 にする（pc4）。
- 中立の書き換えの回数 NS_ROUNDS を 2 から 3 にする（ns3）。

設計（dcomp-nine から。注文処理は変えない）:

- 穴埋めの山登り（filler climb）で、各目標と供給元の今の寄与を保存し、交換のたびの再計算を省く。元の浮動小数点の順序と乱数列は保つ（solutions/dcomp-climb-cache と同じで、出力は変わらない）。
- 空いた時間で、最良の完成した割り当てから穴を引き継ぐ仕上げを 1 回足し、既存の 8 候補と合わせて 9 候補から V で選ぶ（`dv_candidates = 9`、`dv_chosen` は 0〜8）。

予算はすべて固定で、時刻による打ち切り・候補数の切り替え・軽い注文処理はない。ログ・@paper / @ops・実験の切り替え・プロファイラ・DesignStore・段の目印は親と同じ。
