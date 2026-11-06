# deval-vcache

改良元: `solutions/deval-vclean`。

V が重複して構築していた 130,023 通りの順序制約の期待費用表を、窓割当ての PosetSums と共有する。既存の正逆両方向の和に、正規化した向きの費用を 16 bit 配列 1 本追加し、向きごとの正確な期待費用を引く。V の数式・係数・候補作成は親と同じ。起動時の重複したハッシュ表作成と大きな表の参照を省く。

`solutions/deval-vselect/optimize_value.py` で生成する。`verify_value_table.cpp` は全 318 クラス × 720 通りの置換で、元の和と方向別の値を検査する。候補と時間ガードは親の設定を使う。
