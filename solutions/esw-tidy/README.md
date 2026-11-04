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

## 手元の評価だけの違い（LOCAL_BENCH）

`-DLOCAL_BENCH`（scripts/pahcer_run.py が付ける。ジャッジでは定義されない）のときは、倍率込みで 1.80 秒を過ぎても注文処理の軽い計画（fast_mode）に入らず、最後まで通常の計画で処理する。マシンの負荷で手が変わらないようにするため。stderr の fast_requests は常に 0 になり、かかった時間は end_sec に出る。変更は main の「main: requests」の段の `#ifdef LOCAL_BENCH` の 1 か所だけ（ほかに LOCAL_BENCH で働くのは下の設計の保存と読み込み）。

設計の段の時刻による打ち切り（窓の割り当て 0.50・0.61、緊急設計に切り替える 1.30・1.35、焼きなまし 1.205、穴埋めの山登り 1.26、再割り当て 1.345、穴あけ 1.39、補助紙の表をあきらめる 1.45）は、LOCAL_BENCH でもそのまま。

## 設計の保存と読み込み（LOCAL_BENCH、scripts/pahcer_run.py の --save-design / --design-from）

注文処理だけの変更を、同じ設計の上で比べるための仕組み。`-DLOCAL_BENCH` のときだけ働き、提出版の動作は変えない。

- 設計の結果（注文処理に要る状態）を `DesignState` にまとめた: 汎用紙の数 M・汎用窓の数 G・取っ手の数 H、窓の並べ替え、並べ替えた後の目標、比較器の対と色、穴あけの後の 192 枚の紙、各紙の列、各目標の紙、取っ手の窓。
- main の設計の段（窓の割り当て〜穴あけ）を関数 `design_papers` に移し、Solver の準備を `make_solver`（DesignState から Solver を作る）にした。main は「設計（または読み込み）→ make_solver → 補助紙の表と先読み → 紙の出力 → 注文」の順になる。穴あけは design_papers の中で、印刷したままの紙から作った Solver の上で行い、その結果の紙を DesignState に戻す（main は穴あけの後の紙から Solver を作り直す。元の Solver と同じ中身になる）。計算と時計を読む回数は改良元と同じ。
- 環境変数 `DESIGN_SAVE_DIR` があると、設計の終わり（補助紙の表と先読みを作った後、紙を出力する直前）に、DesignState と、補助紙の表を作り終えたか、design_papers の stderr、プログラム開始からの経過時間を `<dir>/<hash>.txt` に書く（hash は入力のバーコードの FNV-1a。注文の列だけが違う入力は同じファイルを使う）。
- 環境変数 `DESIGN_LOAD_DIR` があると、設計をせずにそのファイルを読む（ないか、入力と合わなければ `design_store_error` を出して終了コード 1 で終わる）。保存した stderr と `design_loaded = 1` を出し、Solver・補助紙の表（保存した run で作り終えていなければすぐにあきらめる）・先読みを作り直す。設計の終わりで、時計がそこから保存した経過時間の続きを読むように開始時刻をずらす。そのため、注文処理の stderr（req_sec、end_sec、helper_end_sec など）も元の run の時間の続きになる。
- 注文処理のコードが同じなら、読み込んだ run は保存した run と同じ紙と操作を出す。注文処理を変えた解法でも、DesignState の形が同じならその設計を読み込める。

確認（時計を、読むたびに一定時間進む擬似時計に置き換えた版で）: seed 0〜39（1 回 20 µs）、40〜55（200 µs。設計の各段が早く打ち切られ、補助紙の表をあきらめる）、56〜60（2 ms。緊急設計）の 61 件で、(1) LOCAL_BENCH なしで改良元と stdout・時計を読む回数が一致、(2) LOCAL_BENCH で改良元と一致、(3) 保存した run と読み込んだ run の stdout が一致し、stderr も `design_loaded` の行と、補助紙の表をあきらめたときの helper_papers（読み込んだ側は途中までの数が違う）を除いて一致（end_sec などの時刻も一致）、(4) 同じバーコードで注文の列だけを変えた入力でも、保存したファイルが同じで、元の入力の設計を読み込んだ run が、その入力で保存した run と同じ stdout、(5) LOCAL_BENCH で軽い計画を止めないようにした版（時刻で手が変わる）でも保存と読み込みの stdout が一致（読み込みで時計をずらさない版では 6 件中 6 件が不一致）。実時計でも、gcc と clang の版で保存と読み込みの stdout が一致した（4 件ずつ）。
