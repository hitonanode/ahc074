改良元: solutions/d30a-stack1

filler climb の代理利益の重み。reset=6 と返却費用0.8へ変わった基準で、旧最適値0.5を検査する。

パラメータ: climb=0.7。LOCAL_BENCH の環境変数: D30B_KCLIMBSCALEVALUE（既定 0.7、基準値 0.5）。

A担当の reset_strength、covered_gain の返却費用、fret-full と V の回帰係数は変更しない。固定反復回数、時計倍率、設計保存、既存のログを維持する。
追加 stderr 指標 `audit_parameter` は今回のコンパイル既定値。環境変数を使った場合は実効値と異なる。
