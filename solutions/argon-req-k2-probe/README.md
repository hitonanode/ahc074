改良元: solutions/argon-req-ejectstats-v2

異なる紙集合を持つDP第2解を、通常の候補一覧へ入れずに独立して最後まで仕上げる測定版。基準の状態・出力を必ず復元し、将来の注文を読まない。追加計画の実装は solutions/argon-req-k2-v3 と同じ。共通のprocessへ候補を渡し、編集済み・eject済みの結果がキャッシュにあれば引き継ぐ。測定用の仮の最終経路はheavy traceへ出さない。

joint_probe_raw/duplicateは有効な追加元計画数と、通常計画のどれかと初期積層が同じ件数。joint_probe_<stage>_<gate>_*のstageは0:未編集、1:編集済み、2:eject済み、gateは基準完成値との差の上限0/.25/.5/1/2/無制限。trials/valid/same/better/gain/saved/ceiling/secは試行数・有効数・同じ完成積層数・完成評価値改善数・改善合計・改善時の即時手数差・正の即時手数差の合計・仕上げ時間。ceilingはこの候補集合の局所的な手数機会を測るだけで将来の実現スコアの厳密な上界ではない。

既存の全ログ・スイッチ・プロファイラ、CLOCK_SCALE、LOCAL_BENCH、DesignStore、目次・節を保持する。固定設計で測定し、時間を超える測定専用版を通常評価する場合だけ--no-recordを使う。
