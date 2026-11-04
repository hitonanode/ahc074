改良元: `solutions/opsearch-fast`

注文処理の初期積層・評価・再生を再利用し、1→1の挿入位置を絞って2→2交換と別計画の短縮へ時間を回す。終了表示を担当する2枚の交換を優先し、同紙の再操作や既に短い手順を再短縮候補として優先する。目的関数と、操作の可視性・表示・キャップ・補助紙回収の検査は継承する。

既定は **`F2_MODE=1`**（1.5倍予算向け）。**`F2_MODE=2`** は2.0倍予算向け。実測と適用範囲は [REPORT.md](REPORT.md)。`F2_MODE=0` は旧opsearch-fastと同じ探索、`NEUTRAL=0` は追加探索全体を止めてesw-fixiterの標準出力を再現する。

| 設定（F2_は表で省略） | MODE=0 | MODE=1（既定） | MODE=2 |
|---|---:|---:|---:|
| NS_ROUNDS: 改善時の中立段の最大周回 | 2 | 1 | 2 |
| REPEAT_MIN: 次の周へ進む評価改善量 | 0 | 0 | .05 |
| NS_TWO: 2→2も使う | 0 | 1 | 1 |
| ONE_ANCHORS: 1→1の挿入先数（0は全列挙） | 0 | 2 | 2 |
| POST_CANDIDATES: 保持する計画数 | 2 | 3 | 8 |
| PLAN_SCREEN / PLAN_SKIP_EDITED / PLAN_DISTINCT | 0 | 1 | 1 |
| PLAN_SHORTLIST: 完全短縮に進む条件 | 0: 制限なし | 2: 現在より短い | 0: 制限なし |
| PLAN_LIMIT / PLAN_EJECTS: 追加計画数 / eject反復上限 | 99 / 4 | 1 / 2 | 1 / 2 |
| CANDIDATE_MODE / CANDIDATE_PRIORITY | 1 / 0 | 2 / 1 | 2 / 1 |
| PROMISING_SLACK: 有望候補だけの許容差 | 0 | .75 | .75 |

各設定は初回だけ読む。`F2_` を付けた個別の環境変数はMODEより優先し、この版だけに作用する。次いで旧版と共通の非接頭辞名を読む。例: `F2_MODE=2 F2_NS_ROUNDS=1`。下記の共通値は全MODEで同じ。

- `NS_ONE=1`、`NS_PAIR_FILTER=1`（2→2の削除紙2枚がともに終了表示の担当）。`NS_TRIPLES=0`、`NS_RECHECK=0`、`NS_SHORT_ROUNDS=0`。
- `NEUTRAL_WIDTH=2`、`NEUTRAL_DEPTH=2`（候補へ編集パスを適用）、`NEUTRAL_SLACK=.25`。PROMISING_SLACKは、既に親より短いか同紙の再操作がある候補だけに適用する。
- `CANDIDATE_MODE=2` は、新紙に加え、既存紙の操作回数が親より増えた候補も保存する。`CANDIDATE_PRIORITY=1` は短い手順、再操作の多い手順、評価値の順。署名が同じなら評価値の低い方を残す。
- `PLAN_SCREEN=1` は追加候補を単独削除だけで予備短縮して評価値順に並べる。`PLAN_SKIP_EDITED=1` は通常段の2計画を省き、`PLAN_DISTINCT=1` は現在の最良手順・状態と同じ候補を省く。
- `PLAN_SHORTLIST=1` は既に短いか再操作あり、2は既に短いもの、3は現在以下の手数に絞る。`PLAN_PRIORITY=1` は再操作を優先、2は手数を先に優先（既定0）。`PLAN_GAP=1e9`、`PLAN_STOP=0` は評価差による足切り・最初の改善での停止を無効にする。

出力を保つ再利用は全MODEで有効。

- 注文内で初期積層と区間表示の疎表を共有し、アンカー変換にバイト配列を使う。
- `MEMO=1`: 同一後処理内の終了リンク全体を照合し、正規化・回収可能性・評価の状態項を共有。経路の可視性は別に検査する。
- `PREFIX=1`: 編集列の紙・アンカー・ラベルが一致する合法な前半だけを再利用。
- `PLAN_REUSE=1`: 生の計画・ラベル・状態が一致する場合に、通常段で済ませた処理を共有。
- `LAZY_TAIL=1`: ejectの色・被覆検査を通る修復紙があるときだけ、末尾の位置を作る。
- `PAIR_OWNERS=1`: 2枚修復の元の必要条件から第2紙が一意に決まる場合を使い、通る紙対と順序を保って列挙を省く。

実験用の比較設定も残す（全て既定0）。`CANON=1` は未変更の列区間をまとめて正規化、`SHARED_VIS=1` は全紙の可視時点を共通再生で作る、`CROSS_MEMO=1` は旧補助紙の優先順も照合して注文内のパス間でメモを共有する。これらは出力一致を検証したが速度改善が小さいため使わない。`ONE_LIMIT` は1→1の改善採用数、`JOINT_LIMIT` は2枚修復の合法な削除手順の試行数、`JOINT_STOP` は最初の改善での停止、`THREE_HIDDEN/THREE_EXTRA` は3→2の最初の削除紙を終了時不可視紙/開始時の補助紙へ絞る。`REFINE_BEST` は改善した最良手順だけへの編集・eject反復数、`COLLECT=0` は中立候補の保存を止める（COLLECTだけ既定1）。旧NS_*の詳細は[改良元](../opsearch-fast/README.md)を参照。

stderrには継承した `ns_*`、`neutral_*`、`triple_*` に加え、次を `名前 = 数値` で出す。

- `f2_plan_reused/skipped/wins/screens`: 編集結果の再利用、省略、別計画での採用更新、予備短縮の数。
- `f2_memo_hits/misses`: 終了状態メモの照合数。`f2_prefix_steps/replay_steps`: 省略/再生した編集数。
- `f2_refine_calls/saved`: 最良手順だけの追加短縮回数/純削減手数。
- `f2_canon_bulk/steps`、`f2_visibility_tables/queries`: 実験用の区間正規化の紙数、共有可視表の作成/参照数。

LOCAL_BENCHの `HEAVY_TRACE=1`、`HEAVY_PREDICT=1` は継承した `#heavy` / `#heavycand` を出す。`PLAN_TRACE=1` は `#f2plan r rank reused input_len final_len input_gap edited_gap gain won baseline_len repeats added` を出す。SCREEN有効時のinputは予備短縮後、addedは基準に対する操作紙の多重集合の増分。これらの行に `=` は入れない。すべて既定0。

紙属性・操作ラベル・CLOCK_SCALE・LOCAL_BENCHの全力処理・設計の保存/読み込み・提出時のPacerを継承する。新規修復操作のラベルは `repair`。
