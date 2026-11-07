# deval-funded650

改良元: solutions/deval-vbranch-o3。生成スクリプト: ../deval-speed/make_combined.py。

Hungarian法の4列SIMD更新、穴あけの整数DP・被覆範囲共有・変化したサンプルだけの再構築、短いfiller列の内部保持を組み合わせる。

窓割当て 650,000 回、filler climb 25,000 回、穴あけの色サンプル 16 個。4分岐を穴あけ前のVで選別し、上位2候補だけ最後まで仕上げる。 一次選別前に再割当て1回、通過後に1回。

設計の保存・@paper/@ops・段の目印・時間ガードを維持。LOCAL_BENCHでは注文探索予算は固定。
