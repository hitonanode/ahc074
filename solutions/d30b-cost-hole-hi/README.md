改良元: solutions/d30a-stack1

handle-hole の修復費用の重み。複数穴をまとめて直す注文処理に対する限界費用を検査する。

パラメータ: hole=0.532。LOCAL_BENCH の環境変数: なし（整数SIMDと定数畳み込みを維持）。

A担当の reset_strength、covered_gain の返却費用、fret-full と V の回帰係数は変更しない。固定反復回数、時計倍率、設計保存、既存のログを維持する。
追加 stderr 指標 `audit_parameter` は今回のコンパイル既定値。環境変数を使った場合は実効値と異なる。
