改良元: solutions/dcomp-combo-alt1

終状態memoのindex用ハッシュを4本の独立したFNV鎖で計算する。後続配列193byte全体による衝突検査と、各経路の合法性再生は元通り。計算結果そのものは近似しない。

設計・要求の固定予算、ログ・trace・profiler・実験スイッチ、目次と段、DesignStoreは保持する。時計による切替はない。
