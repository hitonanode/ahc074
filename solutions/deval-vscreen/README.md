# deval-vscreen

改良元: `solutions/deval-vpipeline`。

前半 2 段を共有した 12 分岐から、再割当て 1 回だけを行った状態の V16 で上位 2 候補を選ぶ。選んだ候補だけ filler climb 50,000 回、再割当て 1 回、穴あけと最終再割当てまで仕上げて V16 で決定する。予備選別の全候補で filler climb を省くことで候補数を増やす。

`DEVAL_REHEAT` を z とすると、分岐開始時の温度倍率は 1, z, z² の繰り返しで、終端では全て 1 に戻す。既定 z=1。総反復数、時間ガード、保存形式は親と同じ。生成は `solutions/deval-vselect/make_screen.py`。
