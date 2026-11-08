改良元: solutions/dcomp-combo-alt1

plan_costがgeneric境界とgeneric permutation rankを別々に同じprefixを走査して求めていたため、一回の走査にまとめる。rankは元の整数漸化式・紙順を保ち、future表の同じ値を返す。

要求の候補・計算の加算順・予算は変更しない。両コンパイラ共通。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持し、時計分岐なし。
