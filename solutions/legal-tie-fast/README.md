# legal-tie-fast（legal-tie-fix の出力を変えない高速化）

改良元: `solutions/legal-tie-fix`。main.cpp は `solutions/legal-roll/make_tie_solver.py tie_w_gap03.json`（高速化を入れた版）で作った。

## 改良元からの差分

- 仕上がった計画を記録するとき、その注文でそれまでに記録した最小の plan_cost より kTieGap（0.3）以上高い計画は記録しない。最後の選択の plan_cost はその最小以下なので、比べ直しの対象（差 0.3 未満）から外れる計画だけを省く。
- 比べ直しの対象が 1 つもない注文では、特徴の計算を省いてすぐ戻る。
- 選ぶ計画は legal-tie-fix と同じになるはず（設計固定の比較で確かめる）。指標は legal-tie-fix と同じ。
