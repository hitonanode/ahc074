# deval-vrecip

改良元: `solutions/deval-vreheat`。

焼きなましの handle 費用で、AVX2 の除算を逆数近似と Newton 法 1 回に変える。スカラー初期化も同じ逆数で計算し、変更のない要素の差をゼロに保つ。float の丸めが変わるので探索経路は変わる。分岐の温度倍率は 2。その他の候補作成・V16・保存形式・時間ガードは親と同じ。

再生成: `solutions/deval-vselect/make_recip.py`。実測で速度と新しい注文列のスコアを確認して採否を決める。
