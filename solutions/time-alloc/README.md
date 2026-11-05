改良元: solutions/esw-memo

設計の焼きなましに使っていた時間の一部を、注文ごとの探索に回す版。時間配分だけを変える。探索方法・評価関数・乱数生成器・候補の作り方は変更しない。次の既定予算をソースに直接設定する。

- NS_ROUNDS既定値: 1 → 2
- 通常の後処理候補 kPostCandidates: 2 → 3
- kAnnealIters: 14900000 → 11175000

窓割り当て450,000回と山登り133,000回、焼きなまし4区間、フィラー山登り154,000回、再割り当て4回は維持する。上記以外の予算は改良元と同じ。既存の実験スイッチ・ログ・プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、@paper/@opsと段の目印をすべて保持する。F3_*やMAP_ITERS等の既存の環境変数も引き続き予算を上書きする。比較では基準にも届くこれらの変数を設定しない。

主な指標は、map_end_sec / anneal_end_sec / climb_end_sec / match_end_sec / perforation_end_sec / helper_end_sec（各段の終了時刻）、req_sec（注文計画の合計時間）、end_sec（終了時刻）、gobj_after / model_cost / proxy_after（設計の評価値）、total_moves / self_wrong / op_label_errors（操作数・誤表示・ラベル不整合）。ジャッジ時間は1.04×helper_end_sec + 1.35×req_sec + (end_sec−helper_end_sec−req_sec)で推定する。

比較結果と採否はsolutions/time-alloc/REPORT.mdに記載する。
