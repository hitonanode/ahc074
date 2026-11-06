# deval-vgeneric

改良元: `solutions/deval-vclean`。

handle の目的値を変えず、generic のペア費用だけを再校正する実験。ペア費用の表を作る際に倍率 `DEVAL_GENERIC_SCALE`（既定 1.3）を掛ける。`DEVAL_GENERIC_CURVE=1` では V の generic 1–3 次モーメントと列費用の係数から作った曲線に置き換える。これらは設計時の代理費用だけを変え、実際の紙と注文処理の規則は同じ。表を前計算するため、焼きなまし 1 手の計算量は増えない。

分岐・仕上げ・V による選択・時間ガードは親と同じ。生成は `solutions/deval-vselect/make_generic.py`。
