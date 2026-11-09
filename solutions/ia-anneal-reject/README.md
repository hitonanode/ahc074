改良元: solutions/dcomp-combo-dual30。

column_moveに既存の「列から一方の色が消えるなら必ず棄却」の判定を、target_move、multi_move、handle_swapにも適用する。正確な列費用の増加が10000を超える場合のみ、元のacceptが消費する乱数1回を消費して重い穴費用の評価を省く。色が消えない手の受理規則は変えない。

乱数列、費用式、固定反復数、候補順、DesignStore、属性出力を保つ。出力同一性とGCC/Clangの時間を小さなprobeで調べるための試作で、最終版ではない。
