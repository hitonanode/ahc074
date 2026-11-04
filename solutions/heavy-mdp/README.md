# 重い中立探索 + 列の部分列 MDP（heavy-mdp、計測用）

改良元: solutions/opsearch-heavy（Astra の重い中立探索）に、solutions/colmdp（列の部分列 MDP）の差分を当てたもの。設計は esw-fixiter のまま（filler climb の λ は 1.0）。

列 MDP の入った状態の価値のもとで、時間を気にしない重い探索がどこまで届くか（探索の伸びしろの上限）を測るための版。提出用ではない。環境変数は opsearch-heavy と同じ（重い設定は NS_ROUNDS=5 NEUTRAL_WIDTH=48 NEUTRAL_SLACK=2 NS_SHORT_ROUNDS=6 POST_CANDIDATES=8 NS_ONE=1 NS_TRIPLES=1）。`COLMDP=0` で列 MDP を止める。
