改良元: solutions/argon-req-ejectstats-v2

採用済みの追加ejectの先に、中立探索を追加した場合の残余利得を同じ開始状態から測る。試行後は必ず基準のeject後の状態・経路へ戻すため、実際の操作列と次の要求の開始状態は基準を保つ。未来の注文は読まない。

seed_probe_<gate>_* は追加eject後と基準最終計画との評価値差の上限0/0.1/0.25/0.5別の試行数trials、正当な計画数valid、基準を改善する件数better、改善時の即時手数差saved、正の即時手数差ceiling、完成評価改善gain、追加仕上げ時間sec。ceilingはこの候補集合で観測した即時手数機会であり、任意の将来スコアに対する厳密な上界ではない。既存の全ログ、スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、節と目次を保持する。
