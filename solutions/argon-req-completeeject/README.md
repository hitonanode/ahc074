改良元: solutions/argon-req-completefast-v3

二つの状態価値付き共同DP計画のうち、編集済みだが通常の勝者としてejectを受けていない候補を再利用する。現行完成値との差が0.5以内の別積層にだけpolish_ejectsを追加し、厳密に改善すれば採用する。同じ編集済み積層は重複処理しない。

設計・目的関数・既存候補・予算を維持する。将来の注文を参照しない。既存のログ、環境変数、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、段の目印と目次はすべて残す。新しい環境変数はない。

value_seed_trials/valid/acceptsは追加eject数、有効数、採用数。gain/savedは完成評価値差と採用時の即時手数差の和で、総実現手数の差とは区別する。
