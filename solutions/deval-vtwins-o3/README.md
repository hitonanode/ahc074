# deval-vtwins-o3

改良元: `solutions/deval-vtwins`。

焼きなましの前半2段を共有し、後半を3分岐（各1/3の反復数）する。各分岐を固定saltを変えて2回ずつ仕上げ、計6候補をV16で選ぶ。filler climbは25,000回、再割当ては1回。焼きなましの合計反復数はSOTAとほぼ同じ。

GCCでは設計の関数だけO3で最適化し、fast-mathは使わない。Clangは既定の最適化。Vの表共有、積分点の圧縮、未使用実験経路の除去、提出用の設計・注文ガードは親と同じ。LOCAL_BENCHでは緊急打切りと注文の軽量化を無効にする。保存する設計は採用候補で、診断と段の目印を維持する。

`FROZEN.json` の設定を `../deval-vselect/finalize.py --o3-design` で固定した。評価項目は `deval-vbranch-o3` と共通。
