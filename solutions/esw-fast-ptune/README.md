# esw-ptune の定数と esw-fast の高速化（esw-fast-ptune）

改良元: solutions/esw-ptune

solutions/esw-ptune（esw-noprune の注文処理の定数を調整した版）に、solutions/esw-fast の高速化（esw-noprune との差分）をそのまま入れた版。出力は esw-ptune と同じで、注文処理が速い。

- 高速化の中身は solutions/esw-fast/README.md と同じ。esw-ptune の定数（`grep -n esw-ptune main.cpp`）は、esw-fast が書き換えた plan_cost の部分（kFillerCharge = 0.7、汎用層の下の穴埋め紙の残存の基準 0.3）にも入れてある。
- 時計を「読むたびに一定時間進む擬似時計」に置き換えると、stdout と時計を読む回数が esw-ptune と一致する（trial_log.md）。
- stderr の指標は esw-ptune と同じ。
