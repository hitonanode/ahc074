改良元: solutions/argon-des-perf-latew105

D5の時間超過を許した計測版。基準が既に後処理した候補を保存し、最後の勝者と
異なる終了順序の上位2候補（元の費用差0.5以内）を次注文の先読みで選ぶ。
次の255目標を全列挙し、3通りの軽いrun_planの最良値（操作数＋既存の終状態価値）を平均する。
現在の注文と同じ次目標は除く。実際の将来の注文は参照しない。
判定は現在の操作数＋次注文の期待費用。選ばれるのは既存の合法な操作列だけ。

固定設計からpahcer_run.pyで実行し、時間超過の計測なので--no-recordを付ける。
ARGON_D5_ON=0で選択を止めた出力対照、SAMPLESの既定255（小さくすると固定seedで抽出）、
GAPの既定0.5、PHIの既定1。いずれも接頭辞ARGON_D5_。
d5_requests/multi/candidates/selectedは注文数/複数状態を持つ注文数/評価候補数/選択変更数。
d5_light_trials/invalidは先読み計画試行/不正計画数、secは先読み段の時間。
d5_static_betterは、元の費用だけでも最後の勝者より安い保存候補の数（0を想定する）。
gainは予測改善、now_deltaは当注文の操作増、next_moves_gain/next_phi_gainは次注文側の予測改善。
全て手/注文。selected_sdは採用時の次目標間の費用差標準偏差、samples95は有限母集団の
分散から符号判定95%に必要な標本数を近似した値（厳密な保証ではない）。
gate0〜5は元の費用差0/.02/.05/.1/.25/.5以内の候補がある注文数と、その候補の予測改善。
既存ログ・指標・プロファイラ・DesignStoreを保持。新しい段と目次は
Request processing: final-candidate rollouts。
