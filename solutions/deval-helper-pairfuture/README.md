改良元: `solutions/deval-helper-future`。

単独/2枚helperの実行前の候補順位に、既存のgeneric末端価値future×0.5を加える。候補数と距離条件は維持する。2枚helperの最少distance内でもfutureの低い状態を先に調べる。状態の優先順はinit_lookaheadで一度だけ安定整列し、距離別のbucketへの投入順に使う。最終のplan_cost、設計、予算は変えない。時計による切替えはない。
