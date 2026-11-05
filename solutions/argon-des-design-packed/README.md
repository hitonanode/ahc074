改良元: solutions/argon-des-perf-stratacut

設計の出力を保つ2つの高速化を組み合わせる。
Comparatorの距離表は、紙番号を付け替えても合法な操作が同じことを利用し、
恒等順序からの1回のBFSと辞書順で先に求めた行の置換で作る。
perms・next・belowと全距離の値・経路の同点処理は同じ。

穿孔の区間DPとキャッシュは、H≤25で25窓の容量を使い、末尾の未使用領域を省く。
H>25では64窓の同じ処理を使う。計算式・順序・候補・採否・乱数・標本数は同じ。
全ログ・@paper/@ops・profiler・予算スイッチ・CLOCK_SCALE・LOCAL_BENCH・DesignStore、
段の目印と目次を保持する。新しいスイッチや指標はない。
