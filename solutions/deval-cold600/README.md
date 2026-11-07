# deval-cold600

改良元: solutions/deval-funded650（高速化の元はdeval-vbranch-o3）。

窓割当て600,000回。温度を全行程で1/2にする。
Hungarian SIMD、整数の穴あけDPと差分更新、短いfiller列の内部保持を使用。4分岐をclimb25k・再割当て1回後にVで上位2個へ選別し、通過した2個を再割当て1回・穴あけ16サンプル・最終再割当てまで仕上げる。

STATE.mdの07:20追記に合わせて、時間不足による候補削減・設計打切り・注文軽量化は外す。探索予算は固定。時計はCLOCK_SCALE経由。DesignStoreは選択した設計を保存し、@paper/@ops・段の目印と目次を維持する。
