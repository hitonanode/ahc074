# clean-base

改良元: solutions/audit4-flip-clk

audit4-flip-clk を、手（出力）を変えずに書き直した版（3753 → 2536 行）。今後の新しい解法のベース。構造と主要な関数の役割は main.cpp の冒頭のコメントにある。

- 削ったもの:
  - 実験用の環境変数（HUB_* / CB_* / BIAS_* / WANT_* / CLIMB_* など約 75 個）と、既定値では通らない分岐。値は定数に固定した。
  - 使われない関数・経路: choose_filler（穴埋め紙の貪欲な選択）、焼きなましの型 0（1 単位の列の移動）と窓のブロック間の移動（choose_blocks の同じ移動は、乱数の消費だけ残す）、表 kBlkTab と kBlock（常に模擬の費用 want_costs を使う）、filler_climb の重みなしの proxy と焼きなまし、焼きなまし後の bias_c / bias_g の計算（filler_climb が上書きしていた）、恒等写像だった紙の ID の振り直し、表の遅延構築、DEBUG_VIS。
  - 前の専用紙・古い穴埋め紙の戻しで「巡回順の前任が列の底」の分岐（is_bottom_without）。canonicalize がその前任を -1 にするので発火しない（run 20261031-235016 の 500 件で 0 回）。
  - 計測用の stderr。`名前 = 数値` は、焼きなまし・山登りの反復数と終了時刻、分割の回数、ブロック数、整合しない対、誤り、汎用層の手数、総手数、注文処理の時間、終了時刻の 13 個。
- 共通化: 区間 DP（best_intervals）、穴埋め紙の利得（filler_gain。焼きなましの線形化した proxy と filler_climb で共通）、段への移動（move_to_level）、列の上の紙（column_tops）、汎用層の要求ごとの充足状態と距離の表（build_abstract で一度だけ作る）、焼きなましの試行と取り消し（attempt）。
- 実験用に残した環境変数は `ANNEAL_ITERS` と `CLIMB_ITERS`（焼きなまし・山登りを回数固定にする。未設定か 0 なら時間で打ち切る）だけ。
- 出力の一致: eqcheck.py（複数の解法を同じ固定回数でテスター経由で回し、stdout を seed ごとに比べる。回数固定の環境変数は元の名前 HUB_ANNEAL も渡す）で、焼きなまし 200 万回・山登り 2 万回の seed 0〜95、600 万回・5 万回の seed 96〜191、整合しない対の罰を 0 にして分割の予備の手段を毎回通す版（元は `CB_KI=0`）の seed 0〜47 で、元の audit4-flip-clk と全件一致。
- 500 件 audit4-flip-clk 比 −0.013 ± 0.061%（run 20261101-005506、256/0/244）、E = 0、WA 0。同じ時間で焼きなましの反復が約 6% 多く、注文処理の時間（req_sec）と全体の時間は元と同じ。
