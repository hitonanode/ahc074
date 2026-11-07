# deval-fixedcfg

改良元: solutions/deval-vbranch-o3。

SearchConfigを通常設定と同じコンパイル時定数に置き換える。実行時のF3_*設定を読み込む経路を除き、通常設定では使わない分岐をコンパイラが消せるようにする。探索の列挙順、予算、評価式は通常設定のまま。SearchConfigのF3_*環境変数はこの版では使えず、設定を変える場合は再生成する。提出用の時間ガードとLOCAL_BENCH時の固定予算を維持する。
