# 終わりの状態の重み 1.3（--design-from の感度の確認用）

改良元: solutions/esw-noprune

注文処理の計画の費用（Solver::plan_cost = 手数 + 残す紙の費用 + kEndWeight × 終わりの状態の将来費用）の kEndWeight を 1.0 から 1.3 にしただけの版。設計は改良元と同じ。scripts/pahcer_run.py の `--design-from`（保存した設計の上で注文処理だけを比べる）と通常の `--compare` で、同じ注文処理の変更の差・標準誤差・所要時間を比べるために作った。改良を狙ったものではない。
