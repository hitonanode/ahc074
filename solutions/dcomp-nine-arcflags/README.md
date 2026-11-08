改良元: solutions/dcomp-nine

窓探索のSIMD relation更新で、forward/reverseの8bitフラグを直接broadcastし、laneごとの可変右シフトとmaskで有向辺へ展開する。256要素の方向表からのランダムロードを省く。各laneのbit0/16は元の表引きと厳密に同じで、辺方向のshiftと後続処理は不変。

探索回数、乱数列、9候補、浮動小数点演算、注文処理、CLOCK_SCALE、ログ、実験スイッチとプロファイラを保つ。時間不足の切替なし。
