改良元: solutions/dcomp-combo-dual25

family選別前の修復で状態の不要なsave/restoreを省く。merge_double_movesは紙順と記録を変更せず、操作列と計測カウンタだけを変更する。元の操作列はmoveで退避・復元し、修復用だけをコピーする。候補の順と費用計算は変えない。

固定予算・時計による軽量化なし。CLOCK_SCALE、DesignStore、@paper/@ops、ログ・実験スイッチ・profiler、段と目次を保持する。
