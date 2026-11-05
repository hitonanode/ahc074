改良元: solutions/argon-req-ejectstats-v2

solutions/argon-req-k2late-fast と同じ第2解の独立処理を行い、安い編集後の特徴別に費用と採用利得を測る。探索の候補・順序・採用条件は変えない。

joint_profile_<i>_* のiは band + 4*repeated + 8*added + 16*length。bandは編集後評価値差が0以下/.25以下/.5以下/それ以上、repeatedは同じ紙の複数回移動、addedは基準最終経路にない紙の移動の有無、lengthは基準より短い/同じ/1手長い/2手以上長い。trials/ejects/accepts/gain/saved/edit_sec/eject_secは試行・eject・採用数、完成評価改善、即時手数差、編集・eject時間。既存ログ・スイッチ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・節と目次を保持する。
