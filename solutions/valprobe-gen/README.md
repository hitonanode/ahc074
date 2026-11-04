# valprobe に汎用層の項を足した計測用の版（valprobe-gen）

改良元: solutions/valprobe

valprobe（中立探索の置き換え前後の 2 状態から同じ乱数の注文列を解かせ、価値の見積りの差と実際の差を比べる）に、solutions/genvalue の汎用層の項（`generic_share × future[汎用層の並び]`）を plan_cost の 5 つ目の項として足し、`#vprobe` の価値の項も 5 つ（1 手先の掘り、取っ手の色合わせ、列 MDP、列の外の紙、汎用層）にした。`GENVALUE=0` で plan_cost には足さない（値は出す）。
