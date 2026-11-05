改良元: solutions/esw-slim

R1の測定専用版。実際の出力と次注文へ渡す積層は基準のまま、同じ開始状態の別Solverで「前の商品紙の据え置き」を初期計画に固定し、現在の後処理・中立探索を最後まで実行する。旧フィラーの返却と再利用の両方を試す。未来の注文は読まない。

全ての既存ログ・スイッチ・プロファイラは基準Solver側で維持する。新しい集計は `r1_oracle_all_*`（全ての色安全な据え置き）と `r1_oracle_extension_*`（色付き汎用窓により新たに許可された部分）。requests/valid/same_order/better/move_betterは注文数、value_gainは評価値の改善量、optimistic_movesは将来価値を無視して少ない手数だけ選んだ改善量、selected_movesは評価値で選んだ場合の即時手数差。注文単位のtarget/extension/gain/move_gainも出す。

測定コストを含むreq_secなので採用候補の時間評価には使わない。通常評価なら時間超過の測定版として--no-record、ここでは設計固定評価を使う。
