改良元: solutions/dcomp-combo-dual25

byte配列の紙移動で同じ位置なら直ちに戻る。64 bytes以下のmemmoveは全範囲を先にregisterへ読み、head/tailを同じ順序位置へ書く。整数操作のみ、overlap部分は同じ値を持つ。

計測時計の負荷を含む絶対値は速度利益の推定に使わず、通常版の同時比較とbyte一致で採否を決める。既存ログ・trace・profiler・実験switch・段・DesignStoreを保持。予算・時計分岐なし。
