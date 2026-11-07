改良元: `solutions/deval-flex125-plan3`。実装は `deval-helpeq1` / `deval-helpeq-fast` を経由した。

generic層の並べ替え手数が通常の計画と同じ単独helperも、残るhandle修正を含む事前見積りの上位1件だけ候補に入れる。generic手数を減らす従来候補と合わせて最大6件を実行し、既存のplan_costと後処理で選ぶ。単独helperのgoalは、generic手数が同じなら既存の次注文の期待費用futureが小さい方を選び、さらに同点なら深い挿入位置を使う。

追加探索の時間を確保するため、出力を保つ三つの変更を加えた。

- ejectの整数必要条件を4紙ずつAVX2で検査する。通過候補の順は保つ。
- next-cost cacheのkeyを整数SIMDで圧縮する。全key照合と浮動小数点の加算順は保つ。
- canonicalizeの配列初期化を世代stampに置き換える。旧fillerの順と重複も保ち、unsigned wrap時だけstampを初期化する。

設計の予算・候補数8・初期列順は基準と同じ。注文はNEUTRAL_WIDTH=3、NS_ROUNDS=2、PLAN_SHORTLIST=3。全予算は固定で、時間不足による軽量化・設計打切り・候補数切替えはない。

容量を確保するため、呼ばれない4関数、必ず上書きされる旧MDP分類、古いコメントを削除した。DesignStoreは選んだ設計を保存する。`dv_candidates` / `dv_chosen` は設計選択、`req_sec` / `end_sec` はCLOCK_SCALEを適用した注文時間・終了時刻。元のログ・統計・@paper/@ops・trace・profiler・実験switch・段の目次を保つ。
