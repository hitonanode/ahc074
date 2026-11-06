# deval-vtwins

改良元: `solutions/deval-vcompact`。

前半2段を共有し、後半は2分岐へ半分ずつ反復数を配る。それぞれを異なる固定saltで2回仕上げ、計4候補をV16で選ぶ。焼きなましの合計反復数と仕上げ回数は4分岐案と同じだが、各分岐を長くして、その後の仕上げで多様性を得る。

`DEVAL_RAW_BRANCHES`は焼きなましの分岐数（既定2）、`DEVAL_FINISHES`は各分岐の仕上げ回数（既定2）。`CLIMB_ITERS`と`DEVAL_MATCH_ITERS`は仕上げ予算。後発分岐の温度倍率は2。Vの表共有、提出時のガード、ログと保存は親と同じ。生成は `solutions/deval-vselect/make_twins.py`。
