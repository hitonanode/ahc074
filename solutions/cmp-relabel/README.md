# cmp-relabel（計測用）

改良元: solutions/cmp-ret

解法としては cmp-ret と同じ。環境変数 `RELABEL_STEPS=n` を付けたときだけ、焼きなましの後に、汎用窓のラベル（比べる 2 枚の紙と、どちらが黒か）を、焼きなまし後の対（固定）の汎用層の手数の見積り Σ mean_moves が下がるように n 回の山登りで付け直す。手はラベルの変更・色の反転・2 窓のラベルの交換で、全部の対の整合（関係が非巡回）と 15 組すべての使用を保つ。stderr に `relabel_before` / `relabel_after`（対 1 組あたりの見積り）、`relabel_accepted`、`relabel_sec` を出す。

結果は trial_log の「cmp-ret の上での構造の見直し（bold-）」。
