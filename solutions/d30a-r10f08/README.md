改良元: solutions/dcomp-combo-dual30

reset_strength を 10.0、covered_gain の返却費用を 0.8 とする。reset6 + 返却0.8 の組合せから、reset 需要による頭色復帰の効果をさらに強める。

LOCAL_BENCH の D30A_RESET / D30A_FRET で指定可能。V、固定反復数、返却確率の式は変更しない。

固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。新しい stderr 指標はない。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。

返却費用を変えるのは covered_gain。ProbabilityHead の確率勾配と穴あけの区間DPは親の返却費用0.6を保つ。これらも揃えた実験は d30a-fret-full に分ける。
