改良元: solutions/nogen-helper-order

SOTAのargon-des-design-packedに含まれるComparator距離表の高速化を移植する。
恒等順序から1回だけBFSを実行し、紙番号の置換で残りの距離行を得る。
距離と最短経路の同点順序、所有商品・紙模様・探索予算は変えない。
背景の全ペアが比較窓を持つ構造なので、番号の置換は同じ遷移グラフを表す。
通常の監査・時間指標・DesignStore v2・時間ガードを継承する。
