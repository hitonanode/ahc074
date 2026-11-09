改良元: solutions/d30a-reset6

穿孔の追加穴費用で使う reset 需要を 2*demands から 6*demands へ変更する。先頭色確率に使う需要は従来の2倍を保つ。
費用と確率の両方を6倍にしたd30b-stack2の次の切り分け。climb/rematchの確率を6倍にしても新基準では利益が残らなかったため、穿孔でも費用の較正だけで改善を得られるか確かめる。

LOCAL_BENCHではD30B_KPERFRESETで費用側の倍率を変更できる（既定6、2で基準）。reset_strength、covered_gainの返却費用、Vの回帰係数は変更しない。固定反復回数、CLOCK_SCALE、DesignStore、既存のログと段目次を維持する。追加stderr指標なし。
