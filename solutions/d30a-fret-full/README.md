改良元: solutions/dcomp-combo-dual30

reset_strength=6、仕上げの穴埋め紙の返却費用=0.8。covered_gain に加えて、その確率勾配（ProbabilityHead::probability_gradient）も同じ係数にする。穴あけの区間DPは、配置・返却の合計を1.6から1.8にする。整数DPの単位を1/5手から1/10手へ変え、0.1刻みの返却費用を整数で表す。すべての利益・上界・所有紙補正を同じ倍率で割り戻す。V自身の費用は学習時のまま。

LOCAL_BENCH の D30A_RESET は reset 係数、D30A_FRET は返却費用（0.1刻みに丸める）。D30A_FRET_FULL=0 は新たに揃えた勾配・穴あけDPだけを0.6へ戻し、d30a-stack1と同じモデルにする対照用切替。DPの整数倍率が倍になるだけの対照では、順位・実数への割り戻しを保つ。

固定反復で、新しい時計読み・打切り・フォールバックはない。CLOCK_SCALE、LOCAL_BENCH、DesignStore、@paper/@ops、既存のログ・プロファイラ・切替・段の目印と目次を保つ。新しいstderr指標はない。評価は solutions/impla-notes/PROGRESS.md。
