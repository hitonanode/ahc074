改良元: solutions/argon-des-perf-latew105

D4の小係数を検証する。plan_costに0.1×future[汎用紙の順序]を加える。
futureは汎用窓に穴を持つ目標に条件付けた既存の平均最短距離。
0.1はこの値への絶対係数（旧genvalueの約0.555より小さい）。
後処理の完全な紙順序をキーとするmemoにも同じ項を入れ、memoの有無で評価を変えない。
adaptive_next_cost自体とその列だけのキーは変えない。
ARGON_D4_WEIGHTの既定値は0.1、0で項を無効化。
d4_value_callsは値の参照回数、d4_final_futureは各注文終了時のfutureの平均。
generic_moves/total_movesと合わせて、汎用操作の削減と他操作の増加を調べる。
設計、既存ログ・スイッチ・プロファイラ・DesignStore・目次と段の目印を保持する。
