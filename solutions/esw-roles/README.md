# 構造を stderr に出す見本（esw-roles）

改良元: solutions/esw-noprune

改良元に、手元の評価（`-DLOCAL_BENCH`）だけで、解法の構造（紙の役割と、各操作が何のための操作か）を stderr に出す行を足した版。書式は解法に依存しない形で AGENTS.md の「分析」にあり、scripts/observe.py の design・state・queries・stats がこれを読んで表示・集計する。提出版（LOCAL_BENCH なし）の計算と出力は改良元と同じで、LOCAL_BENCH ありでも stdout は改良元と同じ。

## 紙の属性（`@paper <名前> = <出力した紙 0 の値> ... <紙 191 の値>`）

紙の出力の直後に 1 属性 1 行で出す。値は設計の状態（DesignState の列・各目標の紙・取っ手の窓・穴あけの後の紙）から作り、模様からは推定しない。値のない紙は `-`。

- `role`: `cap`（窓 63 の黒い蓋）、`generic`（比較器の汎用紙 6 枚）、`pair`（2 つの目標の紙）、`single`（1 つの目標の紙）
- `col`: 列の紙の列 c（取っ手は h_c）
- `depth0`: 最初の重なりでの列の中の深さ（0 = 列の一番上）
- `hcolor`: 自分の列の取っ手 h_c での色（0 / 1）
- `perf`: 取っ手の穴あけ（Handle perforation）で穴にした取っ手の数。印刷の規則（列 c の紙は h_0〜h_c が不透明、対は 2 つの目標が違う窓が穴）と最終の紙の差で数える
- `targets`: その紙で出す目標（入力のバーコードの番号。`a` か `a,b`）

緊急設計（設計が間に合わないとき）では `role`（`white` / `black` / `blank`）と `window`（その紙の窓）を出す。

## 操作のラベル（`@ops <r> = <ラベル> ...`）

注文 r の操作列と同じ順に 1 操作 1 ラベル。同じラベルが n 個続くところは `ラベル*n` と書く（observe.py が展開する）。操作 0 回の注文は `@ops <r> =`。量を抑えるため、全注文の行を最後（統計の行の前）にまとめて出す。

| ラベル | 操作を作った場所 | 意味 |
|---|---|---|
| `ret` | return_paper（前の注文で持ち上げた紙） | 前の注文の紙を列へ戻す |
| `fret` | return_paper（古い穴埋め紙） | 古い穴埋め紙を列へ戻す |
| `reuse` | run_plan の ret_mode 3、run_joint の x0 | 前の注文の紙を穴埋めの段へ動かす |
| `relevel` | refill_or_return、run_joint | 古い穴埋め紙を別の段へ動かす |
| `gen` | set_generic、補助紙の計画の汎用層の並べ替え | 汎用紙を動かして汎用層を並べる |
| `dig` | lift の掘り | 目的の紙の列を掘る（列の上の紙を列の中へ差し込む） |
| `lift` | move_to_target_top | 目的の紙を一番上（必要なら蓋の下）へ |
| `fdig` | place_filler・place_picked_filler の掘り | 新しい穴埋め紙を取り出すために列を掘る |
| `fill` | place_filler・place_picked_filler | 新しい穴埋め紙をその段へ置く |
| `hdig` | 補助紙の計画（run_interleave・run_interleave_pair）の掘り | 補助紙を取り出すために列を掘る |
| `help` | 補助紙の計画 | 補助紙を汎用層の中へ差し込む |
| `fix` | fix_handles（set_handle） | 取っ手が要求の色になるまで列を掘る |
| `repair` | 後処理の eject（2 削除 + 1 修復） | 修復のために足した操作 |
| `other` | （ラベルを付け忘れた場所） | 出たら付け方の誤り |

- 仕組み: Solver が `ops` と並べて各操作のラベル `op_tags` を持つ。`move` / `move_after` が今のラベル `op_tag` を積み、`OP_LABEL(...)` がそのスコープの間だけ今のラベルを替える（内側が優先。掘りは呼んだ場所のラベルを継ぐ）。計画の候補の保存（best_ops、後処理の候補、計画の後半のキャッシュ、補助紙の計画の初期状態）にもラベルを一緒に写す（`OP_TAG(...)`）。どちらのマクロも LOCAL_BENCH なしでは空になる。
- 後処理（post_optimize）: 操作を「紙 k を紙 anchor の下へ」の編集の列にしてから削除・差し込み先の変更・2 削除 + 1 修復を試すので、編集（Edit）にラベルを持たせた。消えた操作はラベルも消え、差し込み先を変えた操作は元のラベルのまま、何もしなくなった編集は落とし、修復で足した編集は `repair`。最終的な操作列とラベルは 1 対 1 に対応する。
- 注文ごとにラベルの数と操作の数を確かめ、違えばその注文のラベルを出さずに `op_label_errors` に数える（0 のはず）。
- 計算はラベルを読まない。後処理の構造化束縛 `auto [k, a]` を `e.paper` / `e.anchor` に書き換えた（Edit に 3 つ目のメンバを足すため。LOCAL_BENCH なしでも同じ計算）。

## stderr の指標

- `op_label_errors`: ラベルの数が操作の数と合わなかった注文の数（0 のはず）
