改良元: solutions/dcomp-combo-dual30

穴あけ前の V で4分岐を順位付けし、上位2分岐だけ穴あけと後段の再割り当てを行う。その完成後の V が良い分岐を、元と同じ5回の追加仕上げの出発点にする。分岐の乱数状態・salt・ログを保存して再開する。完成後のVが同点なら元と同じ小さい分岐番号を優先する。仕上げ候補の取り違えを抑えつつ、2分岐の後半処理を省く狙い。

LOCAL_BENCH の D30A_PERF_AFTER=0 は元の全候補仕上げ、D30A_PERF_KEEP は仕上げる分岐数（1〜4、既定2）。4は全分岐を仕上げる対照設定。新指標 perf_branch_chosen は完成後に選んだ分岐番号、perf_raw_first は穴あけ前の最良分岐番号、perf_full_candidates は全体で後半まで仕上げた候補数（既定7、元は9）。DEVAL_DUMP_FEATURES=1 は選んだ分岐を前後2回記録する。dv_first は最初の分岐の穴あけ前、dv_best は完成後の値。

固定反復・決定的な乱数列を保ち、時間による打切りや新しい時計読みは加えない。CLOCK_SCALE、DesignStore、@paper/@ops、既存の指標・プロファイラ・切替・段目次を引き継ぐ。評価と採否は solutions/impla-notes/PROGRESS.md に記録する。
