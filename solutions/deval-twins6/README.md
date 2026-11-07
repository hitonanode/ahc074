# deval-twins6

改良元: solutions/deval-sixpolish2（設計・注文の元はdeval-vbranch-nofb）。

焼きなまし前半2段を共有し、後半を3分岐へ分ける。各分岐の予算は1/3で、合計は元とほぼ同じ。各分岐を固定saltを変えて2回仕上げる。filler climbは各50,000回、再割当て1回、穴あけ8サンプル、穴あけ後の再割当て1回。

6候補すべてを完成させ、Vで選ぶ。 Hungarian SIMD、穴あけ整数DPと差分更新、filler列の内部保持、列の連続区間走査、丸めた確率差分の共有を使う。

固定予算・固定乱数で、時間不足による探索削減はない。DesignStoreは選ばれた設計を保存し、@paper/@ops・目次・段の目印を保つ。
