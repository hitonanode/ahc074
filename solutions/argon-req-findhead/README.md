改良元: solutions/argon-des-perf-stratacut

後処理の紙位置検索 find_paper で、先頭16枚を SSE2 で比較してから残りを従来の memchr で調べます。紙順は192枚の置換で、最初の一致位置は変わりません。先頭付近で繰り返すライブラリ呼び出しを省きます。

候補・順序・計算結果、全スイッチ・ログ・プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore は維持します。メンバ配置は変えず、新規スイッチ・指標はありません。既存コードと同じ x86 の SSE2 を使います。
