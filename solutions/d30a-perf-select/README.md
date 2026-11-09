改良元: solutions/dcomp-combo-dual30

4 つの焼きなまし分岐を filler_climb と最初の再割り当てまで仕上げ、穴あけ前の V で 1 分岐を選ぶ。その分岐だけ穴あけ・後段の再割り当てを実行して V を計算し直す。選んだ分岐の乱数状態と salt を引き継ぐ。後続の 5 回の仕上げは元と同じで、毎回現在の最良候補を出発点にする。選ばれなかった 3 分岐の重い仕上げを省く。

全 9 候補を評価し、V は選んだ分岐の仕上げ後にもう 1 回評価する。dv_first は最初の分岐の穴あけ前の値、dv_best は従来と同じ完成設計の値。chosen_log は選んだ分岐の前半と後半をまとめ、後続候補が勝てばその候補のログに置き換える。

LOCAL_BENCH の D30A_PERF_AFTER=0 で元の全分岐仕上げに戻る。新指標 perf_branch_chosen は穴あけ前に選んだ分岐番号（0〜3、切替無効時 -1）、perf_full_candidates は穴あけと後段再割り当てを行う候補数（通常 6、元は 9）。DEVAL_DUMP_FEATURES=1 では選んだ分岐の @deval_final が前後の 2 回出る。

固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。
