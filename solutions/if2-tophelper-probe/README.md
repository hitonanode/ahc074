# if2-tophelper-probe

改良元: solutions/dcomp-combo-dual30

計測だけの版（出力は同じ）。try_helpers で、前の注文の紙（上に持ち上げたまま）や古い穴埋め紙が、
今の注文 u の補助紙の表 helpers[u] に載っているかを数える。
- top_helper_orders: 前の紙が helpers[u] にある注文数
- top_helper_saving: その紙を補助紙に使ったときに減る汎用層の手数の和（戻した後の状態からの見積り）
- top_helper_deep: 戻した後の深さが 5 を超えて候補から外れた数
- filler_helper_orders: 古い穴埋め紙のどれかが helpers[u] にある注文数
