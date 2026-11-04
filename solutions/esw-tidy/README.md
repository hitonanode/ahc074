# eject-single-window の整理版（出力は同じ）

改良元: solutions/eject-single-window

eject-single-window の main.cpp を、出力を変えずに読みやすく整理した版。今後の解法のベースにする。アルゴリズム・パラメータ・乱数・時計の読み方は改良元と同じ。

## 段の構成

各段の始まりに `// ==== <段の名前> ====` の行を置き、ファイル冒頭のコメントに同じ名前を順に並べた目次を置いた。`grep -n '// ====' main.cpp` で目次と各段の行番号が分かる。段は次のとおり。

- 共通部分（定数・時計・乱数）、汎用層（6 枚の比較器、半順序ごとの平均手数の表 PosetSums）
- 窓の割り当て（対の関係の高速評価、焼きなましと山登り assign_windows）
- 設計（単位・列・費用の模型と初期割り当て、焼きなまし、穴埋めの山登り、先頭を考えた再割り当て）、補助紙の表（Interleave）
- Solver（紙と取っ手、将来費用の模型、重なりの操作、計画の各部（選択肢と区間 DP、run_plan、穴埋めの連鎖、補助紙）、記録の正規化）
- 後処理（削除と差し込み先の変更、2 削除 + 1 修復）、注文処理（process）、緊急設計、取っ手の穴あけ（Perforation）
- main の各段（入力、窓の割り当てと初期設計、焼きなまし〜再割り当て、紙の印刷、Solver の準備、穴あけ、補助紙の表、模擬、紙の出力、注文、統計）

## 消したもの

いずれも実行されないか、結果に効かないもの。

- 常に同じ値の実験用の切り替えと、その使われない分岐: PRIORITY_NUM（= 20。列の費用は重み付き深さだけになる）、FILL_DEMAND_WEIGHT・DEMAND_MODE、ANCHOR_RESEARCH、VERIFY_* の検査、Solver の切り替え（scan_fixes、packed_bits、scan_tops、byte_links、replay_mode、post_link_filter、post_rewrite_mode、mid_filter・mid_once・mid_possible・mid_fast・mid_eject_mode、lazy_positions、min_eject_errors）、Perforation の切り替え（freeze_heads、head_candidates、screen_weight、crossing_cache、skip_equal）、rematch_probability の dynamic・derivative、filler_climb の demand_weight・head_mix（どちらも 1）、assign_windows の g == 36 の分岐、`if (true)`。
- 切り替えの裏で使われていなかった旧版: choose_fillers_dp・choose_fillers_prelift・run_joint の旧版、fix_costs_old、handle_bits_old と hidx、post_optimize の int リンク版と replay_mode 0 / 2 の再生、Perforation::full_profit と solve_edges の skip。
- 呼ばれない関数と未使用のメンバ: Comparator::mean_moves、closure8、Design::hole_table、set1_u64、pick_nonzero、Solver::G、Design::M、WindowStats::score、出力しない計数（position_builds、rewrite_same_paper、Perforation の screened など）。

## 書き方の整理

- clang-format（Google 系、字下げ 4、120 桁）で全体を揃え、1 行に詰め込まれていたコード（PR 90 で足された部分）を分けた。自明でない関数にコメントを足した。
- 重複していた処理をまとめた: 時計の読み（scaled_since。読む回数は同じ）、関係の推移閉包（WindowRelations::closure）、pext による弧の取り出し（implied_arcs）、assign_windows の受理（take_move、candidate_cost、evaluate_pairs）、計画の費用（Solver::plan_cost）、差し込み先の候補（anchor_candidates）、先頭の選び方（ProbabilityHead::heads）、取っ手の表（Solver::set_handles）。
- 後処理の 2 削除 + 1 修復を post_optimize から eject_repairs に分けた。Perforation は先頭を最初に一度だけ選ぶ（改良元でも固定だった）ことを使い、試す紙を total_profit の引数で渡す形にした。
- 残したもの: `-DSIM_HARNESS` の模擬（SIM_SEQS）、反復回数を固定する環境変数（MAP_ITERS、GOPT_STEPS、ANNEAL_ITERS、CLIMB_ITERS）、CLOCK_SCALE の仕組み、stderr の `名前 = 数値` の指標（名前は同じ）。

## 出力が同じであることの確認

時間で打ち切る解法なので、元と整理後の両方の時計を「読むたびに一定時間だけ進む擬似時計」に置き換えてビルドし（探索量が時計を読む回数だけで決まる）、テスターに通した stdout を比べた。tools/in/ の seed 0〜119（1 回の読みで 20 µs）、120〜159（200 µs。設計の各段が早く打ち切られ、注文の途中から軽い計画になる）、160〜199（`-march=native`）、200〜239（clang++）、240〜249（2 ms。初期設計が間に合わず緊急設計になる）の計 250 ケースで、stdout はすべて一致し、時計を読む回数も一致した。
