# deval-vkick

改良元: `solutions/deval-vreheat`。

第2候補以降は、分岐直前に列全体と専用handleを一緒に2回入れ替え、別の局所解へ移るきっかけを作る。距離は1–6列。ペアの適合性と各列の両色を維持したまま、費用を再計算して通常の焼きなましで修復する。分岐温度の倍率は2。その他は親と同じ。

`DEVAL_KICKS` が入替回数、`DEVAL_KICK_DIST` が最大距離。再生成は `solutions/deval-vselect/make_kick.py`。
