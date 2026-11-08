改良元: solutions/dcomp-nine

annealのcolumn_moveで、差分SIMD配列の構築と取っ手費用の評価を8列ずつ融合する。元の整数差分・FMA・除算・横方向加算順序を保ち、全列分の差分配列を同時に生存させない。

探索の乱数列、固定反復数、候補数9、受理規則、V、注文処理を保持する。近似演算やfast-mathなし。CLOCK_SCALE、@paper/@ops、DesignStore、段の目印、実験スイッチとプロファイラを保ち、時間不足の切替は加えない。
