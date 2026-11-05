改良元: solutions/argon-req-filldp-positive

R2の旧紙価値の測定専用版。実際の出力は基準のまま、同じ開始状態の別Solverで共同DPの計画を後処理まで単独で仕上げる。mode 0は採用済みの共同DP、1は旧紙の価値差、2は返却による自列の色修正の補正も含むもの、3/4はそれぞれ従来重みとの中間。将来の注文は読まない。

old_probe_<mode>のvalid/raw_existing/same/better/gain/movesは有効計画数、初期積層が既存候補にもある数、完成積層が基準と同じ数、完成評価値改善数、その改善合計、その場合の即時手数差。residual_*はmode 0も十分処理した場合に比べて、旧紙重みの4案を追加した残りの改善。ceilingは手数だけを見て選ぶ楽観値。

既存ログ・スイッチ・プロファイラを維持し、常に0のvalue_filler_zero/value_filler_zero_usefulは削除。測定版は固定設計で使う。通常評価で時間超過となる場合は--no-recordとする。

old_gate_<mode>_<g>は、初期候補のplan_costが基準の完成値から一定以内の場合だけ仕上げる条件の測定。g=0..6の幅は0, 0.25, 0.5, 1, 1.5, 2, 3。calls/better/gain/movesは条件に入る数、完成値の改善数・改善量、その時の即時手数差。ゲートは完成前にわかる値だけを使う。
