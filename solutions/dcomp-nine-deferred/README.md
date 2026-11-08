改良元: solutions/dcomp-nine

dcomp-nine-fusedに加え、column_moveで新しい穴数の保存を受理まで遅らせる。棄却時は新しいQだけ保持する。受理時には元と同じ小整数加算を再計算してn0/n1へ保存する。費用式と評価値は変えない。

探索の乱数列、固定反復数、候補数9、受理規則、V、注文処理を保持する。近似演算やfast-mathなし。CLOCK_SCALE、@paper/@ops、DesignStore、段の目印、実験スイッチとプロファイラを保ち、時間不足の切替は加えない。
