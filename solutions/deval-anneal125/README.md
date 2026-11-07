# deval-anneal125

改良元: solutions/deval-funded650（高速化の元はdeval-vbranch-o3）。

窓割当ては元の450,000回。前半2段と4分岐の形はそのまま、焼きなましの反復予算を1.25倍にする。
各分岐をclimb25k・再割当て1回後にVで上位2個へ選別し、通過した2個を再割当て1回・穴あけ8サンプル・最終再割当てまで仕上げる。Hungarian SIMD・整数の穴あけDPと差分更新・短いfiller列の内部保持を使う。

STATE.md07:20に合わせ、時間不足による候補削減・設計打切り・注文軽量化は外す。固定予算、固定乱数。DesignStoreと@paper/@ops・目次を維持。
