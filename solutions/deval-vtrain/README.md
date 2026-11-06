# deval-vtrain

改良元: `solutions/deval-vclean`。候補ごとの教師データを作るため、`DEVAL_FORCE_PICK` が指定されたとき、その番号の候補を出力する。既定では親と同じく V の最小を選ぶ。注文処理は親と同じで、保存した各候補を標準スクリプトで 8 注文列に再生する。再学習に使う seed は 0–499 のみ。

生成は `solutions/deval-vselect/make_training.py`。提出用ではない。
