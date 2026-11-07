# legal-roll-open（段階 2 の研究版。提出用ではない）

改良元: `solutions/legal-roll`。違いは冒頭の設定の既定値だけ: ROLL_MODE 8（開ループ: SOTA の選択を保ち、32 注文ごとに SOTA の候補それぞれの費用を共通の 48 本 × 5 注文で記録する）、ROLL_NEW 0、ROLL_EVERY 32、ROLL_S 48、ROLL_H 5、ROLL_VAL 0。仕組みと指標は solutions/legal-roll/README.md。

このディレクトリの main.cpp は、評価した時点の legal-roll（変種の由来 5・6 と ROLL_Z を足す前の版）から作った。評価に使ったソースは runs/20261108-045003_legal-roll-open/src/ にある。
