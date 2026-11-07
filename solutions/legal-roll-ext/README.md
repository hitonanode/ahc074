# legal-roll-ext（段階 2 の研究版。提出用ではない）

改良元: `solutions/legal-roll`。違いは冒頭の設定の既定値だけ: ROLL_MODE 8（開ループ）、ROLL_N 1、ROLL_NEW 0、ROLL_EVERY 1000000、ROLL_S 96、ROLL_H 5、ROLL_VAL 0、ROLL_EXT（段階 2b の表示を目標にした探索で見つけた短い列を、その注文で SOTA の選択と比べる）。仕組みと指標は solutions/legal-roll/README.md。
ROLL_EXT は solutions/legal-search/results/disp_ext.txt（ext_candidates.py で作る）。
