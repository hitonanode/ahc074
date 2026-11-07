# deval-perf8

改良元: solutions/deval-vbranch-o3。

穴あけの期待利益を測る層化サンプル数を32から8に減らす。他の設計段・選択V・注文処理は同じ。

時間ガード、DesignStore、@paper/@opsは維持。LOCAL_BENCHでは注文探索予算は固定。
