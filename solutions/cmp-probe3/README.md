# cmp-probe3（計測用）

改良元: solutions/cmp-anneal

解法としては cmp-anneal と同じで、焼きなましの係数を環境変数で変えられるようにしただけ（指定がなければ同じ値）。`A_T0`（開始温度 ×100、既定 2.0）、`A_T1`（終了温度 ×1000、既定 0.015）、`A_SWAP`（ハンドル交換の率、千分率、既定 150）。
`P_M` / `P_G`: 汎用紙の枚数と汎用窓の数（既定 6 / 36）。
`P_TOP` / `P_END` / `P_FCH`（×100）: 注文処理の kTopPenalty（0.35）、kEndWeight（1.0）、kFillerCharge（0.6）。
