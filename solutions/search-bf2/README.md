# search-bf2

改良元: solutions/gen-bf2 と solutions/search-ops（合流）

- 紙の設計（土台 + 反転紙の汎用層、焼きなまし、整合しない対の修復）は gen-bf2 のまま。
- 注文ごとの操作は search-ops の計画探索と穴埋め紙をそのまま移した（前の専用紙・穴埋め紙を列の上端 / 下端のどちらへ戻すか、穴埋め紙を使うか、対の相方が続いたら据え置くか、の全組み合わせを試し、「手数 + 列の外に残した穴埋め紙の数」が最小の計画を採る）。説明は solutions/search-ops/README.md。

## 移植で変えたところ

- search-ops では汎用層の操作が MDP グループの部分目標だったが、ここでは gen-bf2 の set_blocks（土台 F と反転紙 F_b の並べ替え）を使う。専用紙の G の穴が触れるブロックごとに、穴の窓で A_u に近い向きを選んで set_blocks に渡す（wanted_blocks）。この部分は gen-bf2 と同じ。
- 穴埋め紙の条件（一番上の紙なら掘りを 3 手以上省く、深さ p の紙なら p + 3 手以上、1 注文 4 枚まで）、計画の費用、可視性の検査は search-ops と同じ。

## パラメータと指標

- 環境変数: gen-bf2 のもの（`HUB_H` = 36、`CB_S` = 4、`HUB_TL` = 1.2 秒など）と、search-ops のもの（`SEARCH`、`FILLER_DEPTH` = 3、`MAX_FILLERS` = 4）。
- stderr: gen-bf2 の設計側の指標（`blocks`、`uncovered`、`inconsistent_pairs`、`repaired_pairs`、`model_*`、`anneal_end_sec` など）と、search-ops の注文側の指標（`kept_partner`、`fillers_used`、`total_moves`。`partner_hits` は出さない）。gen-bf2 の `dig_per_ded`・`tri_per_ded`・`flips_per_ded`・`touched_blocks_per_ded`・`g_holes_per_ded`・`handle_holes_per_ded` はなくなった。
