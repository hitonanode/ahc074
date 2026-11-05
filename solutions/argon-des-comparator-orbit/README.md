改良元: solutions/argon-des-perf-stratacut

Comparator::build_tablesの距離表を、全始点BFSから1回のBFSと紙番号の置換で作る。
操作は紙の位置だけで定まり、紙番号を一括して付け替えても合法な遷移と距離は変わらない。
恒等順序からの距離だけをBFSで求め、他の始点は先頭の非固定位置を直す交換で
辞書順の小さい始点に帰着させる。距離表の各行・各列の番号と値は元と同じ。
perms・next・below、経路の同点処理、設計・注文の候補・乱数・反復予算は維持する。

新しいスイッチ・指標はない。af_comparator_tables_secがこの処理の既存の計測値。
全ログ・@paper/@ops・profiler・予算スイッチ、CLOCK_SCALE・LOCAL_BENCH・DesignStore、
段の目印と目次を保持する。変更はGeneric layerのComparator::build_tablesだけ。
