改良元: solutions/d30a-stack1

ProbabilityHead の filler 利益の重み。初回1.0と穿孔後1.25の比を保って同時に倍率補正する。勾配と最終受理の両方に適用される。

パラメータ: rematch=0.7。LOCAL_BENCH の環境変数: D30B_KREMATCHSCALE（既定 0.7、基準値 1.0）。

A担当の reset_strength、covered_gain の返却費用、fret-full と V の回帰係数は変更しない。固定反復回数、時計倍率、設計保存、既存のログを維持する。
追加 stderr 指標 `audit_parameter` は今回のコンパイル既定値。環境変数を使った場合は実効値と異なる。
