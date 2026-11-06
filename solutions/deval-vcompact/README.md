# deval-vcompact

改良元: `solutions/deval-vbranch`と同じ設定の `deval-vreheat`。

前半2段を共有し、後半を4分岐、後発候補の開始温度を2倍にして、完成状態をV16で選ぶ。filler climbは50,000回、再割当ては2回。未使用の分割・途中状態選別・軽い予測モデルと保存フックを除き、提出用に整理した。Vの費用表は既存の厳密表と共有する。

追加候補を1.12秒で止めるほか、提出時には窓探索0.85秒、窓climb0.90秒、設計anneal1.15秒、filler climb1.25秒を緊急打切りの目安とする。注文処理は残注文の比率qに応じた1.84−0.12q秒 / 1.90−0.30q秒の2段階ガード。緊急打切りと注文軽量化はLOCAL_BENCHでは無効。保存設計と診断は親と同じ。

`FROZEN.json`の設定を `../deval-vselect/finalize.py --share-table --prune-branch` で生成した。V・候補の統計項目は `deval-vbranch`と同じ。
