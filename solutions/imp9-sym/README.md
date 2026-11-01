# imp9-sym

改良元: solutions/imp-lean

設計で使う対の汎用層の費用（Design の gcost、gc = 2 gcost）を、対の 2 目標の両側の平均にした（solutions/gpt6pro-09-01-legal-dist の「制約 C とその反転の和」）。

- 元: gcost[a][b] = mean_moves(A_a, A_a ^ A_b)（番号の小さい目標 a の向きだけ）。lean-g で汎用層の距離を「最下段の紙を動かさない」合法な最少手数にしてから、この値は向きで変わる（目標 b に要る関係は a の関係の反転で、反転した半順序の期待手数は一般に違う）。
- 新: gcost[a][b] = (mean_moves(A_a, A_a ^ A_b) + mean_moves(A_b, A_a ^ A_b)) / 2。対の紙は両方の目標に同じ頻度で使われるので、こちらが実際の期待手数。
- gcost は Design::initialize の対の選び方（0.65 × ハンドルの違い + 2 gcost + 0.04 × 違い）と、焼きなましのモデル（gc）の両方で使われる。

mean_moves はメモ化されているので、追加の時間は小さい。ほかは imp-lean と同じ。
