改良元: solutions/d30a-stack1

穿孔の色確率と追加穴費用に残った reset 需要倍率。両方を同時に変え、焼きなましの reset_strength=6 は維持する。

パラメータ: perfreset=6.0。LOCAL_BENCH の環境変数: D30B_KPERFRESET（既定 6.0、基準値 2.0）。

A担当の reset_strength、covered_gain の返却費用、fret-full と V の回帰係数は変更しない。固定反復回数、時計倍率、設計保存、既存のログを維持する。
追加 stderr 指標 `audit_parameter` は今回のコンパイル既定値。環境変数を使った場合は実効値と異なる。
