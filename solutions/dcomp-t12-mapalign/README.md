改良元: solutions/dcomp-combo-dual25

GCCで窓割当の関数・loopの配置を明示して命令境界の影響を測る。窓割当関数本体のサイズはalt1/dual25で同じだが64byte内の開始位置が異なるため、この仮説を一度検証する。Clangは元のコンパイル設定を維持する。計算・乱数・探索量は同じ。

予算は両コンパイラ共通の固定値。時計での軽量化なし。既存ログ・trace・profiler・switch・段と目次・DesignStoreを保持する。
