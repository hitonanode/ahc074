改良元: solutions/dcomp-combo-alt1

anchor候補の小さな動的vectorを固定容量の配列へ変更する。候補順と重複除去は同じ。戻り値はNRVOを使い、heap確保をなくす。

固定探索予算、既存ログ・実験スイッチ・profiler・目次と段、DesignStoreは保持。時計による分岐は追加しない。
