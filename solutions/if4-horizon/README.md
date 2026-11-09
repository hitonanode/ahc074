# if4-horizon

改良元: solutions/dcomp-combo-dual30

注文処理だけの変更（設計は同じ）。最後の注文（r = R−1）では、計画の終わりの状態は二度と使われないので、
plan_cost の終状態の項（filler_charge、kEndWeight × adaptive_next_cost、generic_bias）を 0 にして手数だけで選び、
近い同点の補正（tie_choice）も行わない。Solver に `end_scale`（終状態の項の重み）を足し、main が注文ごとに設定する。
LOCAL_BENCH の環境変数 `HORIZON_TAIL=n` で最後の 1+n 注文に広げられる（探り用。既定は最後の 1 注文だけ）。
