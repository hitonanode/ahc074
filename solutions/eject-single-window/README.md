# 不一致1窓も途中の修復対象にする

改良元: solutions/eject-small-error（提出用の元はsolutions/tight-thirty-eight）。

2操作を削除して1操作で修復する後処理で、削除後に不一致が1窓だけの場合も調べる。修復紙の種類・可視性の検査・挿入位置・将来費用は従来と同じ。2窓以上だけを調べていた条件を緩め、表示差が小さくても途中の可視性を改善できる計画を拾う。

紙の設計・制限時間・CLOCK_SCALEは変更しない。min_eject_errors=1を固定した提出可能な候補。後処理の試行数はeject_trials、受理数はeject_accepts、処理時間はreq_secへ含まれる。
