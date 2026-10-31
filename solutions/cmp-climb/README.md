# cmp-climb

改良元: solutions/cmp-time

焼きなましの後（1.10 秒）から 1.15 秒まで、clean-base 系の filler_climb（pool-climb）を足した。

- filler_climb: 同じ種類（対どうし・単独どうし）で、両方の列のハンドルで同じ色の 2 つの単位の列を入れ替える山登り。列の費用と汎用層の費用は変わらず、ハンドルの穴の費用（持続モデル）− kW × 穴埋め紙の proxy が下がれば受理する。proxy(t) = t より深い各列 c について、c の紙が段付きの穴埋め紙として t の穴を覆う数（持続で重み付け、3 引き）の列内平均の和（filler_gain は clean-base と同じ）。入れ替えで変わるのは列 a, b の和だけなので差分で評価する。kW = 0.3。
- 動機: gpt6pro-06 の設計は、clean-base 系の焼きなまし後の山登りを持っていない。模擬（焼きなまし・割り当てを回数固定、32 本の乱数注文列）で、seed 24〜87 で −0.083 ± 0.018%（48/16）、seed 88〜215 で −0.089 ± 0.011%（100/28）。kW 0.15 は同じ、0.6 は +0.06%。
- 実験用の環境変数を足した: `CLIMB_ITERS`（回数固定、−1 で山登りなし）、`CLIMB_W`（kW ×100）、`MAP_G`（汎用窓の数の初期値）、`MAP_M`（汎用紙の枚数）。
- stderr: `climb_iterations`、`climb_accepted`、`proxy_before` / `proxy_after`（目標あたりの proxy）。
