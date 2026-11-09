改良元: solutions/dcomp-combo-dual30

仕上げの covered_gain における穴埋め紙の返却費用を 0.6 から 0.8 にする。配置 1 手の費用は保ち、返却が必要な確率に掛ける係数だけを注文処理に近づける。この関数を共用する filler_climb、ProbabilityHead、穴あけに同じ変更が効く。

LOCAL_BENCH の D30A_FRET で係数を指定でき、0.6 で元に戻る。

固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。新しい stderr 指標はない。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。

返却費用を変えるのは covered_gain。ProbabilityHead の確率勾配と穴あけの区間DPは親の返却費用0.6を保つ。これらも揃えた実験は d30a-fret-full に分ける。
