# legal-roll-s32（段階 2 の研究版。提出用ではない）

改良元: `solutions/legal-roll`。違いは冒頭の設定の既定値だけ: ROLL_EVERY 16、ROLL_S 32（SOTA の候補からのロールアウトでの選択を、標本を 4 倍にして 16 注文ごとに）。仕組みと指標は solutions/legal-roll/README.md。

このディレクトリの main.cpp は、評価した時点の legal-roll（変種の由来 5・6 と ROLL_Z を足す前の版）から作った。評価に使ったソースは runs/20261108-045003_legal-roll-s32/src/ にある。
