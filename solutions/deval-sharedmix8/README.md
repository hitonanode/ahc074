# deval-sharedmix8

改良元: solutions/deval-sharedclimb8。

元の4完成候補を保持し、良い2分岐のclimb後から追加するmatchingで、filler価値の重みを0.5・1.5に変える。各重みで各分岐を1回ずつ仕上げ、全部で8完成候補からVで選ぶ。元の候補は重み1.0、穴あけ後の再割当ては全候補1.05のまま。乱数saltも親と同じ固定値。

時間予算・探索回数は親と同じ。時間不足による切替えはない。DesignStore、@paper/@ops、ログ、目次・段の目印を維持。
