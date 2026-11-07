# deval-qtable

改良元: solutions/deval-vbranch-o3。

焼きなましの穴数は整数、resetは2×整数なので、qfの正確なfloat値を表にする。必要になったresetだけを同じSIMD除算で一度生成し、後の段・分岐でも共有する。既存のAVX2で8項を参照する。最大約68MBの未初期化領域を確保し、実際に使うresetのページだけに書く。
候補・乱数・浮動小数点の演算結果と時間ガードを保つ。
