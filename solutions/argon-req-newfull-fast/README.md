改良元: solutions/argon-req-ejectstats-v2

新しいフィラーの共同DP重みを、旧紙をすべて返し、汎用層を編集し、要求紙を持ち上げ、残るハンドルを直した完成計画同士の差で計算する追加案。旧紙の保持・再配置の重みと既存の候補は変えない。候補ごとに共通な返却と汎用層編集を一度だけ実行し、その積層・操作列・ラベルを再利用する。各候補の評価値には共通操作の手数も含める。

比較用の非共有実装は solutions/argon-req-newfull-only。old_full_calls/invalidは局所完成計画の評価数と無効数、old_full_plans/better/gainは有効な追加計画数と初期候補最良値を更新した数・改善値。既存のログ、実験スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、目次・節は保持する。既定の探索予算は変更しない。
