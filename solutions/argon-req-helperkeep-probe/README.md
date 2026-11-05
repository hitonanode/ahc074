改良元: solutions/argon-des-perf-latew105

R4の測定版。旧フィラー保持ヘルパー計画（solutions/argon-req-helperkeep）を通常の候補一覧へ入れずに保存し、基準の探索が終わった後にそれぞれ独立して編集・eject・中立探索まで行う。元の開始状態を共通のprocessへ渡し、既に編集・eject済みの候補はキャッシュを引き継ぐ。最終出力・積層は必ず基準へ戻し、未来注文は読まない。

helper_probe_<stage>_<gate>_*はstage=未編集/編集済み/eject済み、gate=完成前の値差上限0/.5/1/無制限ごとの試行数・有効数・同じ積層・改善数・手数差・評価改善・秒数。helper_probe_best_<gate>は注文ごとの最大評価改善の合計で、候補を重複加算しない。既存統計は仮試行も含む。全ログ、スイッチ、プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、目次・節を保つ。

固定設計で測定する。時間超過する測定版を通常評価するときだけ--no-recordを使う。
