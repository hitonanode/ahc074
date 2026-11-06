# deval-vreheat

改良元: `solutions/deval-vclean`。

後半を分岐する際、候補 0 は元の温度を保ち、その他は温度を一時的に上げる。開始温度の倍率 `DEVAL_REHEAT` は既定 4 で、最後の温度は親と同じ 0.015 になるよう指数的に倍率を 1 へ戻す。目的関数と総反復数は同じ。V16 で完成候補を選択する。

候補数、仕上げ、時間ガード、保存形式は親と同じ。生成は `solutions/deval-vselect/make_reheat.py`。
