# legal-roll-pc（段階 2 の研究版。提出用ではない）

改良元: `solutions/legal-roll`。違いは冒頭の設定の既定値だけ: ROLL_MODE 3（局所的な変種を plan_cost で選ぶ。ロールアウトなし。変種が plan_cost の上で SOTA の選択より良いことがあるかの診断用）。仕組みと指標は solutions/legal-roll/README.md。

このディレクトリの main.cpp は、評価した時点の legal-roll（変種の由来 5・6 と ROLL_Z を足す前の版）から作った。評価に使ったソースは runs/20261108-044103_legal-roll-pc/src/ にある。
