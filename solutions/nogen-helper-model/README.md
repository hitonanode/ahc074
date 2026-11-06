改良元: solutions/nogen-owned-g34

背景ヘルパー統合の前に、保存設計・同じ注文処理で候補の順位を測る測定版。解は変更しない。
`study_helper_post_sec` はヘルパー候補ごとの後処理時間。
`study_helper_winners` は後処理後に通常計画へ勝った注文数、`study_rank1/2/3` はその最終勝者が未加工費用の上位1/2/3に入った数（通常計画の最良1候補も含む）。
`study_helper_gain` は通常計画に対する最終評価値の改善量、`study_raw_candidates` は有効なヘルパー候補数。
所有権監査、時計、軽量処理、DesignStore は基準と同じ。
