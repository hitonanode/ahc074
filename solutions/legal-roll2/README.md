# legal-roll2（legal-tie-fix を方策としたロールアウトのデータを取る研究版。提出用ではない）

改良元: `solutions/legal-tie-fix`。main.cpp は `solutions/legal-roll/make_roll2.py` で作った。`-DLOCAL_BENCH` でだけビルドできる。注文処理の出力は legal-tie-fix と同じ（ロールアウトは複製で行う）。

## 改良元との差分

- ROLL_EVERY（12）注文ごとの 1 回、最後の選択（tie_choice）で、plan_cost の選択（番号 0）と、記録した計画のうち plan_cost の差が ROLL_GAP / 100（0.3）未満のもの（plan_cost の小さい順、最大 ROLL_CAP − 1 = 4 個、方策の選択は必ず含める）を、共通の乱数の将来の注文列 ROLL_S（24）本 × ROLL_H（5）注文で、この解法自身（補正つき）の複製で処理し、手数（表示が違えば 2K）+ 最後の plan_cost(0) を記録する。
- 出力: `#rollmat r u 候補数 方策の選択の番号`、候補ごとに `#rc 由来 手数 plan_cost 費用...` と `#rf 特徴...`（solutions/legal-roll の state_features と同じ並び）。
- 方策の反復: このデータで補正を当てはめ直す（solutions/legal-roll/tie_fit.py、検証は tie_apply.py の「方策の選択に対する得」）。
（今の make_roll2.py は、次の注文の費用の内訳 3 列も書く。このディレクトリの main.cpp はその前の版で、評価したソースは runs/20261108-073221_legal-roll2/src/。）
