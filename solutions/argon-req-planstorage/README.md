改良元: solutions/argon-des-perf-stratacut

区間 DP の一時配列を上限 64 列の固定配列にし、filler 配置では必要な深さの紙だけを探します。generic 計画の短い配列は必要量を予約します。候補構築時の小さな動的メモリ確保を減らします。

探索候補・順序・浮動小数点演算を変えない要求処理の高速化です。Solver のメンバ配置を変えず、既存スイッチ、ログ、プロファイラ、DesignStore、CLOCK_SCALE をすべて保持します。新しいスイッチ・stderr 指標はありません。
