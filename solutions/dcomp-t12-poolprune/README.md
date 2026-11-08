改良元: solutions/dcomp-combo-dual25

整列済みの中立候補poolが満杯なら、末尾より厳密に優先順位が低い新候補のState・操作列のcopyを省く。同じsignatureの置換は先に元どおり処理し、同点は元のsortへ渡す。poolのsortと本探索の順は保持する。追加親にも同じ処理を使う。

固定予算、コンパイラ共通の探索量、時計での切替なし。ログ・実験switch・段と目次・DesignStoreを保持する。
