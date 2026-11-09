改良元: solutions/d30a-stack1

climb/ProbabilityHead の先頭色確率だけの reset 需要倍率。焼きなましの reset_strength=6 は維持し、確率側に残った2との不整合を検査する。

パラメータ: headreset=6.0。LOCAL_BENCH の環境変数: D30B_KHEADRESET（既定 6.0、基準値 2.0）。

A担当の reset_strength、covered_gain の返却費用、fret-full と V の回帰係数は変更しない。固定反復回数、時計倍率、設計保存、既存のログを維持する。
追加 stderr 指標 `audit_parameter` は今回のコンパイル既定値。環境変数を使った場合は実効値と異なる。
