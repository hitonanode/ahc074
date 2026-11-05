改良元: solutions/argon-req-filldp-positive

R2の測定専用版。既存の状態価値付き共同DP計画を、plan_cacheの編集・eject済み状態から最後まで仕上げ、基準の完成値を改善するかを数える。結果は出力に採用せず、元の積層・操作列を戻す。既存ログ・スイッチ・プロファイラを保持し、常に0のvalue_filler_zero/value_filler_zero_usefulのみ削除。

seed_probe_<b>_<g>_trials/better/gain/moves/secは条件を満たす追加処理数、完成値改善数、評価値改善合計、そのときの即時手数節約、追加処理の時間。b=(novel*2+best)*3+stage、novelは初期積層が通常の計画と異なるか、bestは初期値が通常計画の最良を更新したか、stageは0:未編集、1:編集済み、2:eject済み。g=0..6は完成した基準値との差の上限0, .125, .25, .5, 1, 2, 10。全紙順序が基準と同じ場合は省く。

時間超過する測定版なので固定設計評価で使う。通常評価をする場合は--no-record。将来の注文は参照しない。
