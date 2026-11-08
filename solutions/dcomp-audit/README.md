改良元: solutions/legal-tie-fast

窓探索の tabu 停滞を計測するだけの版。提案・受理・乱数列を変えない。dc_stall_iters_0/1 は焼きなまし/最後の climb で、4 倍の停滞間隔を超え、退避可能な候補がない反復数。dc_stall_events は連続区間数、dc_max_gap は最後の受理からの最大反復数。

注文処理は改良元と同一。固定反復回数で動作し、時間による省略はしない。
