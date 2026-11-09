改良元: solutions/dcomp-combo-dual30。

adaptive_next_costの列外紙のbool配列extraは、通常の紙役割ではSIMDの比較で代用済みで、partial MDPも本番経路では読まない。この配列の0初期化と記入を例外のscalar key経路へ移し、partial MDPへの未使用引数を外す。PARTIAL_MDP_CHECKでは元配列を作って検査を保つ。

費用、cache key、浮動小数点の演算順、候補、乱数は不変。Clangの自動0初期化でも不要配列を初期化しないよう、配列の宣言自体を例外分岐へ移す。DesignStore、時計、属性出力、段の目印を維持する。小さな速度probe用の試作。
