改良元: `solutions/neutral-port`

注文処理の改善余地を測る研究用。通常の esw-fixiter の計画選択・後処理を同じ開始状態から先に完了し、それを対照として追加探索する。設計、評価関数 `plan_cost`、完全再生による合法性・表示・キャップ・補助紙回収の検査は変えない。

追加できる探索は、通常の候補を増やして各候補を編集・eject の両方で短縮すること、中立段の反復、1→1 修復、3→2 修復。1→1 は削除した1操作の代わりを、修復紙が見える最初・最後の時点へ挿入する。通常の挿入先変更が扱わない紙や、別の補助紙への交換を探す。3→2 は掘り出し・返却・補修の依存をまとめて外すため、3操作を削除して2枚の末尾修復を試す。

設定は static local で一度だけ読む。既定設定の標準出力は neutral-port と同じ。

| 環境変数 | 既定値 | 内容 |
|---|---:|---|
| `NEUTRAL` | 1 | 0 で全追加探索を無効化し esw-fixiter を再現 |
| `NEUTRAL_WIDTH` / `NEUTRAL_SLACK` / `NEUTRAL_DEPTH` | 4 / 0.75 / 2 | 保存候補数・許容評価差・再短縮モード（0なら再短縮なし） |
| `NS_ROUNDS` | 1 | 中立段の最大反復数。評価値が改善しなければ終了 |
| `NS_SHORT_ROUNDS` | 2 | 候補ごとの eject→成功時の編集の最大反復数 |
| `POST_CANDIDATES` | 2 | 2より大きい場合、この数の別計画を編集・eject で完全に短縮。元の2候補選択も別に保持して対照を確定する |
| `NS_ONE` / `NS_TWO` / `NS_TRIPLES` | 0 / 1 / 0 | 1→1・2→2・3→2 の追加列挙 |
| `NS_RECHECK` | 1 | 中立収集段の冒頭でも既存2→1 eject を再実行 |
| `NS_INTERIOR` | 0 | 2枚修復の区間端点に加える内部位置の組数（最大128）。列の境界・既に操作する紙や一般紙の前後を優先し、同じ位置の組、片方が端の組、その他の組の順に試す |
| `HEAVY_TRACE` | 1 | LOCAL_BENCH で対照と操作列が異なる注文を記録 |
| `HEAVY_PREDICT` | 0 | LOCAL_BENCH で再短縮前の特徴と再短縮結果を全候補について記録 |

`#heavy r u operator round before_cost after_cost before_filler before_next after_filler after_next before after` の形式で、操作列は出力番号の `paper:depth:label,...`（空列は `-`）。`next` は `kEndWeight` 込み。対照は実際の当該注文の開始状態から作った通常後処理の結果であり、別 run の積層から取ったものではない。`operator` の eject/22/11/32/plans と direct/escape は最後に最良候補を更新した由来。両方の操作列でラベルを維持し、新規操作は `repair`。ログは最後にまとめて出す。

`#heavycand r round operator rank parent_len candidate_len cost_gap repeats dead removed added final_len shortening_gain parent_gain won` は再短縮候補の記録。`repeats` は同じ紙の2回目以降の操作数、`dead` は終了表示に見えない紙への操作数、removed/added は親との操作紙の多重集合の差、gain は評価値の減少。候補の特徴は再短縮前に計算する。

元の `eject_*`、`triple_*`、`neutral_*` に加え、`ns_rounds`（実行した中立段）、`ns_plan_calls`（追加計画の完全短縮）、`ns_one_trials/accepts`（1→1の完全評価数・採用数）、`ns_three_trials/accepts`（3削除の合法再生数・採用数）、`ns_changed`（対照と異なる注文数）、`ns_saved`（同じ開始状態の対照からの純削減手数）を出す。継承した `triple_*` は2→2と3→2を合算、`eject_*` は1→1も合算する。

この版に専用の時間制限は設けない。研究は LOCAL_BENCH の全力処理で行い、提出用には使わない。紙の属性・操作ラベル・時計倍率・設計保存形式は継承する。
