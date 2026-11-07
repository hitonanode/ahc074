# deval-climbcache

改良元: solutions/deval-fast2。

filler climbで対象の穴・列と供給紙の被覆・色・先頭適格性を保存し、交換する2ユニットだけ更新する。棄却時には同じ情報を復元する。確率計算・加算順・乱数列は変えない。各提案のutility退避用vectorは確保済み領域へコピーし、最大4対象の列挙は固定配列にする。

設計と注文の探索回数は親と同じ。時間不足による切替えはない。ログ、DesignStore、@paper/@ops、目次・段の目印を維持。
