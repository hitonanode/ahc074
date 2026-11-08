改良元: solutions/dcomp-combo-alt1

要求の操作列Movesを24要素のinline格納とし、長い列はstd::vectorへ移す。操作や比較の順序は変えず、live要素だけをコピーする。構造は既存FillerListと同じ方針。両コンパイラで親との出力byte一致と時間を確認する。

固定予算・実験スイッチ・ログとprofiler・目次と段・DesignStoreを保持。時計による切替は追加しない。
