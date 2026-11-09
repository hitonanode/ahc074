改良元: solutions/dcomp-combo-dual30

焼きなましのハンドル穴費用の reset_strength を 2.0 から 6.0 にする。列の需要で頭色が戻る効果を強め、少数色の穴を減らす配置を狙う。refresh_reset が作る値を参照する再割り当ても同じ値を使う。V、filler_climb の明示的な 2.0、再割り当ての strength 引数は変えない。

LOCAL_BENCH の D30A_RESET で値を指定でき、2 で元に戻る。

固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。新しい stderr 指標はない。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。
