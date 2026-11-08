# legal-speed-prof（legal-tie-fast の注文処理の時間の内訳を測る版）

改良元: `solutions/legal-tie-fast`。出力は改良元と同じ（時間を測るだけ）。提出用ではない。

## 改良元からの差分

- 既存の COLFAST_PROFILE の計測を既定で有効にし、時計を時刻印カウンタ（rdtsc）に替えた（読むのが安く、計測で遅くなる分が小さい）。最後に、実行全体の steady_clock と比べて、倍率（CLOCK_SCALE）込みのミリ秒に直す。
- 関数ごとの計測（`cfprof_<名前>_inc` = 中で呼んだ関数を含む時間、`_exc` = 含まない時間、`_calls` = 呼んだ回数。1 ケースの合計、ミリ秒）に、polish（polish_ejects）、note（比べ直しの候補の記録）、tie_features、ns_collect（中立の書き換えの候補を集める post_optimize）、exp_screen / exp_search（追加の候補の軽い選別と本探索）、display を足した。
- process() を順に段に分けて、段ごとの時間を測る（`phase_<段>_ms`、`phase_<段>_calls`。段の和が `phase_sum_ms`）。段は setup（準備）、opts（計画の候補の模擬）、beam（鎖の探索つきの計画）、helpers（補助紙の計画）、post_best（最良の計画の編集）、post_alts（次点の計画の編集）、eject_main（最良の取り出し 4 回）、alternate（使っていない）、expanded（追加の候補）、neutral1 / neutral2（中立の書き換えの 1・2 回目）、weighted（重みつきの計画）、tie（比べ直し）、merge（2 回動かす紙の統合）、failure（計画がないとき）。
- `cfprof_scopes`（計測の回数）、`cfprof_scope_ns`（1 回の計測にかかる時間）、`cfprof_overhead_ms`（その積。計測で増えた時間の見積り）。
