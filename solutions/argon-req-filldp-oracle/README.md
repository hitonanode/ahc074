改良元: solutions/esw-slim

R2の基準軌跡上の測定版。実際の出力と積層は基準のまま、同じ開始状態の別Solverで状態価値付き共同DPを追加した探索を最後まで行う。未来の注文は読まない。

r2_oracle_same/better/worse/neutralは、完成後の積層一致・目的関数改善・悪化・同値の別積層の注文数。value_gain/lossは改善/悪化の評価値の和、move_gainは評価値が良い時の即時手数差、ceiling_movesは手数だけ見て良い方を選ぶ楽観値。zero_*は利得0区間の検討・有望・選択数。注文単位のvalue/movesも記録する。

既存ログ・スイッチ・プロファイラは保持。測定の時間を含むため時間超過の通常評価では--no-recordを用いる。設計固定の測定を想定する。

さらに利得0を含めない共同DPも同じ開始状態で完成まで実行する。`r2_zero_same/better/worse/gain/loss/moves/ceiling` は利得0を含める追加効果（含めない版との比較）。既存の正利得候補の並べ替えと閾値緩和を分離する。
