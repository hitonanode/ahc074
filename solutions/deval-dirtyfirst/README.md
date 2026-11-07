# deval-dirtyfirst

改良元: solutions/deval-vbranch-o3。

穴数が変わらない最初と最後のSIMD群を省く。中央の群には分岐を加えない。
候補・乱数・浮動小数点の演算結果と時間ガードを保つ。
