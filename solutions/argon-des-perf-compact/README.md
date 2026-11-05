改良元: solutions/argon-des-perf-stratacut

穿孔の区間DPとキャッシュの配列容量を、通常の25ハンドルに合わせて特殊化する。
H以下の添字だけを使う不変条件を保ち、これまで使わなかった末尾の領域を減らす。
25を超えるハンドルの設計は同じアルゴリズムを64要素の配列で実行する。
計算の式・走査順・乱数・標本数・候補の採否は変えない。

新しいスイッチ・指標はない。全ログ・@paper/@ops・profiler・予算スイッチ、
CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持する。
変更はHandle perforationと、その呼び出しの容量の選択だけ。
