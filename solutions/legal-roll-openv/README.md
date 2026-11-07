# legal-roll-openv（段階 2 の研究版。提出用ではない）

改良元: `solutions/legal-roll`。違いは冒頭の設定の既定値だけ: ROLL_MODE 8（開ループ、legal-roll-open と同じ）に局所的な変種 3 個を加える（ROLL_NEW 3）、ROLL_EVERY 32、ROLL_S 48、ROLL_H 5、ROLL_VAL 0。仕組みと指標は solutions/legal-roll/README.md。

このディレクトリの main.cpp は、評価した時点の legal-roll（変種の由来 5・6 と ROLL_Z を足す前の版）から作った。評価に使ったソースは runs/20261108-045003_legal-roll-openv/src/ にある。
