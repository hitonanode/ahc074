改良元: solutions/argon-req-ejectstats-v2

抽出直後の状態価値付き共同DPから、紙集合が異なる第2解を保存する。元の後処理候補を押し出さず、通常探索の後に評価する。既にeject済み・同じ最終積層の候補は省き、評価値差1以内の候補だけを通常の編集で整える。編集後の差が0.5以内ならejectを行い、完成評価値が改善した場合だけ採用する。既存の編集済みキャッシュを再利用し、中立探索全体の繰り返しは行わない。

joint_extra_plans/better/gainは第2解の有効数、初期最良値を上回る数と改善量。joint_late_trials/ejects/accepts/gain/savedは追加編集、追加eject、最終採用の件数、完成評価値の改善合計、即時手数差。既存の全ログ、実験スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、目次・節は保持。NEUTRAL=0では追加候補を通常候補として扱う。
