改良元: `solutions/deval-seven-wide`

deval-map-bitsに加え、閉包を再計算する組がない8要素ブロックではpendingへの仮書込みを省く。

関係と候補順を同じに保ち、固定予算で評価する。時間による打切りはない。
