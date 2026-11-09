改良元: solutions/d30a-stack1

汎用層の単独・一様状態からの費用を倍率補正。初期化、焼きなまし、再割り当ての表を同じ倍率で変更する。pair の需要倍率 2 は維持する。

パラメータ: generic=0.7。LOCAL_BENCH の環境変数: D30B_KGENERICSCALE（既定 0.7、基準値 1.0）。

A担当の reset_strength、covered_gain の返却費用、fret-full と V の回帰係数は変更しない。固定反復回数、時計倍率、設計保存、既存のログを維持する。
追加 stderr 指標 `audit_parameter` は今回のコンパイル既定値。環境変数を使った場合は実効値と異なる。
