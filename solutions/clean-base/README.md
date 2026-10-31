# clean-base

改良元: solutions/audit4-flip-clk

audit4-flip-clk を、手（出力）を変えずに書き直した版。今後の新しい解法のベース。

- 削ったもの: 既定値で通らない分岐と実験用の環境変数（HUB_* / CB_* / BIAS_* / WANT_* など約 60 個。値は定数に固定）、使われない関数（choose_filler、焼きなましの型 0 と窓の移動、表 kBlkTab、焼きなまし後の bias の計算など）、計測用の stderr（`名前 = 数値` は反復数・時刻・分割・手数など 10 個ほどに）、ID の振り直し（恒等写像だった）。
- 共通化: 区間 DP（best_intervals）、穴埋め紙の利得（filler_gain）、段への移動（move_to_level）、列の上の紙（column_tops）など。
- 実験用に残した環境変数は `ANNEAL_ITERS` と `CLIMB_ITERS`（焼きなまし・山登りを回数固定にする。未設定なら時間で打ち切る）だけ。
- 出力の一致: eqcheck.py（両方を同じ固定回数でテスター経由で回し、stdout を seed ごとに比べる）で、焼きなまし 200 万回・山登り 2 万回の seed 0〜47、600 万回・5 万回の seed 48〜143、整合しない対の罰を 0 にして分割の予備の手段を毎回通す版（元は `CB_KI=0`）の seed 0〜23 で、元の audit4-flip-clk と全件一致。
- 構造は main.cpp の冒頭のコメントを参照。
