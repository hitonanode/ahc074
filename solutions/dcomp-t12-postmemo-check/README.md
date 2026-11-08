改良元: solutions/dcomp-combo-dual25

同じ注文内で、同じ開始state・操作列・ラベル・modeから通常postを繰り返す時だけ完成結果を再利用する。中立候補を収集する呼出しは対象外。完全キーの比較で衝突を排除し、外側の反復条件で使うeject_acceptsの増分を再現する。F3_POST_MEMO=0で無効化でき、trace・profile時も元の計算へ戻す。チェック版はhitを元関数で全て再計算して、出力・完成state・eject増分を比較する。

CLOCK_SCALE、固定探索予算、両コンパイラ同じ探索量、@paper/@ops、ログ・実験switch・段・DesignStoreを保持する。
