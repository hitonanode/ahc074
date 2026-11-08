改良元: solutions/dcomp-combo-alt1

終状態memoのindex用ハッシュを8本の32bit SIMD鎖で計算する。後続配列全体の衝突検査は保持し、hash一致だけで状態を共有しない。

設計・要求の固定予算、ログ・trace・profiler・実験スイッチ、目次と段、DesignStoreは保持する。時計による切替はない。
