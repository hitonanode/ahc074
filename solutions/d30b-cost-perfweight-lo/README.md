改良元: solutions/d30a-stack1

穿孔の donor 利益の受理重み。複数filler・owner補正が入った後の旧0.7を検査する。DPの返却費用は変更しない。

パラメータ: perfweight=0.49。LOCAL_BENCH の環境変数: D30B_KPERFWEIGHT（既定 0.49、基準値 0.7）。

A担当の reset_strength、covered_gain の返却費用、fret-full と V の回帰係数は変更しない。固定反復回数、時計倍率、設計保存、既存のログを維持する。
追加 stderr 指標 `audit_parameter` は今回のコンパイル既定値。環境変数を使った場合は実効値と異なる。
