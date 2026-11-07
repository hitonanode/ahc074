# deval-refinish-fast

改良元: solutions/deval-refinish8。

親の4+4候補の探索を変えず、covered_gainの初期化とclimb内の幾何情報の再利用を加える。出力一致を比較する。

出力を保つ高速化はdeval-climbcacheと同じ。窓割当て・焼きなまし・注文予算は元と同じで、時間不足の切替えはない。DesignStore、ログ、@paper/@ops、目次・段の目印を維持。
