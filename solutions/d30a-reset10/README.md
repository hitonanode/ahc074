改良元: solutions/dcomp-combo-dual30

Design::reset_strength を2.0から10.0に変える。穴の需要を評価する際に、列への注文によって頭色が戻る効果を強める。返却費用は親の0.6を使い、resetだけの効果を比較する。反復数・候補数・Vは変えない。

LOCAL_BENCH の D30A_RESET で係数を変えられる。2.0が親の設定。新しいstderr指標はない。

固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。新しい stderr 指標はない。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。
