改良元: solutions/dcomp-combo-dual30

焼きなましの reset_strength を 2.0→6.0、仕上げ covered_gain の返却費用を 0.6→0.8 とする。頭色が列の需要で戻る効果と、穴埋め紙の返却負担を強める組合せ。V は変更しない。

LOCAL_BENCH の D30A_RESET と D30A_FRET で各係数を変更できる。元の設定は D30A_RESET=2、D30A_FRET=0.6。単独実装は d30a-reset6 と d30a-fret08。

固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。新しい stderr 指標はない。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。

返却費用を変えるのは covered_gain。ProbabilityHead の確率勾配と穴あけの区間DPは親の返却費用0.6を保つ。これらも揃えた実験は d30a-fret-full に分ける。
