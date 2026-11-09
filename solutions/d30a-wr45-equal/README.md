改良元: solutions/dcomp-combo-dual30

kWindowRate=0.45 とし、窓割り当ての既定反復数を502000にする。450000回・割合0.6の親と同じ設計時間を狙う。490000回でも約9ms余ったため、割合0.45での1反復あたり時間の見積りから12000回を追加する。他の反復数は変えない。

LOCAL_BENCH の D30A_WINDOW_RATE と MAP_ITERS で割合・反復数を指定できる。gobj_after、map_end_sec、dv_best で設計の変化を確認する。新しいstderr指標はない。

固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。新しい stderr 指標はない。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。
