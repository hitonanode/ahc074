改良元: solutions/argon-des-perf-stratacut

後処理の表示フィルタを高速化します。移動紙集合を初期位置で表して区間境界を一括計算する argon-req-filterbits と、区間表に現在の要求との誤色を保存する argon-req-wrongmask を組み合わせます。初期位置が既に分かるので、単紙の誤色参照に追加の逆引きが要りません。

候補、順序、浮動小数点計算、全ログ・指標・スイッチ・プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore を保持します。Solver のメンバの型・サイズ・配置は維持します。新しいスイッチ・指標はありません。
