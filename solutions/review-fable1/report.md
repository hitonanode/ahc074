# review-fable1: solutions/final-time-pace/main.cpp のバグレビュー（Claude）

対象: `solutions/final-time-pace/main.cpp`（600,007 bytes）。読解と、`scripts/pahcer_run.py --no-record` 経由の小さな実行で確かめた。
実行はすべて `solutions/review-fable1/run.py`（jflags-notes/run.py の写し。`JFLAGS_RAW=1` で LOCAL_BENCH なしの本番ビルドができる）。

## 所見（重い順）

### 1. 窓の割り当ての焼きなましが「何も受理しない状態」で止まり、期限まで空回りする（既存のバグ、スコアのみ。minor）

- 場所: `main.cpp:2655-2679`（`assign_windows` の探索ループ）と `:2612-2645`（`propose_candidate`）。
- 何が起きるか: 一部のケースで、探索の早い段階から `propose_candidate` がほぼ毎回 false を返す（tabu / memo の棄却か、elite path の停滞）状態に入り、以後 2000 万回以上ループしても受理が増えない。時間で区切るので TLE にはならないが、割り当てが悪いまま（gobj_after が 11.3。通常は 9.8〜10.0）で以降の設計が進む。
- 証拠（再現）: 本番ビルド run 20261109-025334_final-time-pace（clang, libc++, zero-init, seed 0〜99）の seed 13: `search_accept = 72`, `map_iters = 25279488`, `gobj_after = 11.3149`, Score 10510（同じ seed の GCC 本番ビルド 025334-3 は search_accept 8633, Score 10405）。同じく pattern-init の 025334-2 でも seed 13（accept 72）と seed 84（accept 2749, 2145 万回）。LOCAL_BENCH の clang run 20261109-004131_final-time-pace-6（500 件）では seed 245（accept 30, 2282 万回）・13・448、GCC 標準ビルド 20261109-004131_final-time-pace では seed 105（accept 973, 1958 万回）など。固定反復の dcomp-combo-dual30（20261109-003105, 2000 件）でも seed 508 が 45 万回中 accept 44 なので、時間化より前からあるバグ。頻度は 0.5〜1%。
- 重さ: minor（クラッシュ・WA・TLE ではない。該当ケースのスコアが 1% 程度悪い）。
- 最小の修正案: 探索ループで「受理なしのまま N 回（たとえば 1 万回）連続」を検出したら、tabu/memo の epoch を進めて棄却の記憶を捨てる（`map_reset` で行う `++epoch` と `std::fill(tabu_epoch…, 0)` と同じ）。最終日の変更としては見送りも妥当。

### 2. 再試行の窓の割り当て（G=32, 28）が、絶対期限のために 0 反復になる（本番で未観測。minor）

- 場所: `main.cpp:10902-10938`（`design_papers` の attempt ループ）、`:2652-2657` と `:2733`（`map_search` / `gopt` の期限）。
- 何が起きるか: 最初の設計の `initialize` が失敗すると、G を 32 にして `assign_windows` をもう一度呼ぶ。期限は `design_time.deadline("map_search")` の絶対時刻で、1 回目で使い切っているので、再試行の探索と gopt は it=0 で即座に break し、初期のランダムな割り当てのまま `initialize` を試す。固定反復版では 160,000 反復していた。失敗すれば attempt 2（G=28）も同じで、emergency 設計（1 注文あたり最大 64 手）になる可能性が旧版より高い。
- 証拠（推論）: コードの読解。手元のどの run でも `G = 32` は出ていない（025334 の 300 件、004131 の 500 件すべて G=38）ので、頻度は非常に低い。
- 重さ: minor（本番で観測されない経路。起きれば emergency 設計で T が約 4〜5 倍）。
- 最小の修正案: attempt ≥ 1 のときは `design_time.active` を一時的に false にして旧来の固定反復で探索する。

### 3. ジャッジのビルドでは assert が有効（NDEBUG なし）（minor、情報）

- 場所: 22 か所。特に `main.cpp:10177`（`assert(std::abs(profit - cached_profit()) < 1e-7)` 浮動小数の一致）、`:9986`、`:5808`、`:10532`（`H==25||H==31||H==35`）。
- ジャッジのコンパイルには `-DNDEBUG` がないので全部評価される。手元の評価も NDEBUG なしなので露出は同じで、過去の全評価で発火していない。10532 は G=38/32/28 に対応する H のみを許し、再試行の設計とも整合する。
- 重さ: minor（現状の条件では発火しない）。修正は不要。

## 確かめて問題のなかった範囲

- **時間で区切る設計の段**（`DesignTimePlan`, `:185-285`）: 期限の名前は、使われるすべての段（map_search / gopt、anneal_s0・s1（共有部分）、c0〜c3 の anneal_s2・s3、c0〜c3・c4・c6 の filler、各候補の match/print/perforation/late_match/value、initial_order、helpers）が表にあり、`std::abort()` する「unknown design deadline」には到達しない。候補 5・7・8（extra=2）は filler/match を飛ばす。期限を過ぎた段は it=0 で break し、0 反復でも後続は壊れない（best 状態の復元、`stats.iterations` 0 を割る所はない）。進捗 `progress` は `max(1e-9, …)` で割り、NaN にならない。時計は全部 `elapsed_sec()`（CLOCK_SCALE 込み）。本番 100 件 × 3 ビルドで `design_time_end_sec` 1.22、`helper_end_sec` 最大 1.243、`dt_design_total_sec` 最大 1.224。
- **Pacer**（`:11193-11288`, main `:11651-11689`）: 1 注文につき時計を 2 回読む。`full`/`trip` は常に正、`weight ≥ 8` なので sqrt の 0 割りなし、`left-1 ≥ 0`。LOCAL_BENCH では effort を 0 に固定するが、PACE_SIM ビルドでは本物の Pacer が動く（run 20261109-004131-2〜5: 注文の時計 ×1.0/1.25/1.35/2.0 で end_sec 最大 1.872/1.886/1.887/1.896、pace_light は ×2.0 でも平均 1.9 件）。本番ビルド 100 件 × 3（025334）: 全部 effort 0 か 1、end_sec 最大 1.784（CLOCK_SCALE 1.0、24 並列）。
- **軽い計画（effort 5）**（`:9202-9209`）: 最初に合法だった plan の `ops` をそのまま返す。返す前に `canonicalize()`、`check_vis=false`、`tail_cache_on=false`、`tie_pooling=false` を戻す。`placement_chains` は次の `choose_fillers_prelift` で clear される。`ops.size() > 2K` や表示不一致の plan は候補から除くので、不正な出力にはならない。合法な plan がなければ従来の `plan_failures` 経路。
- **NOINIT の 44 か所**: すべて読んだ。各配列は「個数つきバッファ（nd, n, pool_size, key_size, res_count…）」か「明示的に埋める範囲（fill_n(H) / fill_n(2H)、`first.fill(K)`、`cover[0]=0` + `cover_valid`）」で、読む添字はその範囲内。eject の `ord`/`owned` は owner_stamp で守られ（`:8343-8362`, `:8421-8423` のマスク付き gather）、`prepare_positions`/`prepare_columns` の前に `prepare_order()` が呼ばれる。`NOINIT const auto anchors = anchor_candidates(i)`（`:8201`, `:8222`）は初期化子つきなので属性は無意味だが無害。`ColumnTops` は `all_column_tops` が `counts` の範囲を埋める。実行でも: ASan+UBSan（g++ -O1, run 20261109-025427 の effort 0、030318 の effort 5 と 3、各 24 件）に報告なし、`-ftrivial-auto-var-init=pattern` の本番ビルド（025334-2, 100 件）で WA・クラッシュなし。固定反復の設計で NOINIT あり / なし / pattern-init の 3 本の出力が 100 件すべて一致（run 20261109-030049、下記）。
- **静的診断**: clang 18 で本番のフラグ（libc++, zero-init）に `-Wall -Wextra -Wuninitialized -Wsometimes-uninitialized -Wconditional-uninitialized` を足して `-fsyntax-only`: 警告 0。GCC 13 で `-O2 -march=native -ftrivial-auto-var-init=zero -Wall -Wextra -Wmaybe-uninitialized`: 警告は `:4822` の `-Wmisleading-indentation`（`if(this!=&other)assign(...);return *this;` の 1 行書き。意味は正しい）だけ。
- **コンパイラ別の経路**: 1152/1304/1388/1445/1458/2495/2521/2704（pairs.live の有無）、1650（並べ替えの鍵）、5060/5131/5352（`next_colors` による first[] の早期確定。列の色集合が揃えば以後 first は変わらないので GCC 経路と同値）、7219（PREFIX 既定 0）、7643-7747（screen 使用時はリンク構築を飛ばすが、cap の不変条件は `:7847` で最終順序に対して再検査し、memo は late_memo 経路 `:7855` で扱う）。いずれも同値と判断。
- **本番の経路（LOCAL_BENCH なし）**: `#ifdef LOCAL_BENCH` の塊は、DesignStore、`@paper`/`@ops`、heavy_log の trace、PACE の強制、design の環境変数だけ。本番に必要な処理はその外にある。`OP_TAG` が空になるため `find_cached_plan` の一致条件からラベル比較が抜けるが無害。`Score` の文字列は stderr に出さない。本番ビルド 3 種（clang libc++ zero / clang libc++ pattern / gcc zero、各 100 件、seed 0〜99）と clang LTO ビルド（100 件、seed 100〜199）で WA 0、2 秒超え 0。
- **対話**: 設計の出力後と各注文後に `std::flush`。`-1` か EOF で即 `return 0`。emergency 設計（`:9669-9711`）も同じ。
- **終了処理**: FAST_EXIT なしで通常の return。本番 100 件の実時間の最大は 1.816 s で、end_sec（1.784）との差は 30 ms 程度。
- **有限の仕事の段**: Hungarian（反復数 1〜2）、穿孔 1 パス、V、initial_order、helper 表（limit 1e300）は、反復数か入力の大きさで有界。
- **emergency 設計**: 窓 j の白(j)・黒(64+j) の 2 枚。見えている方を底（d=191）へ送ると他方が見える。1 注文 ≤ 64 手 ≤ 2K。

## 実行した run（すべて --no-record）

- 20261109-025334_final-time-pace{,-2,-3}: 本番ビルド 3 種、seed 0〜99。
- 20261109-025427_final-time-pace: g++ -O1 -fsanitize=address,undefined（LOCAL_BENCH、effort 0）、seed 0〜23。報告なし、WA 0。
- 20261109-030318_final-time-pace / -2: g++ -O1 -fsanitize=address,undefined（LOCAL_BENCH）に `-DPACE_FORCE=5`（全注文を軽い計画）/ `-DPACE_FORCE=3`、seed 100〜123。報告なし、WA 0（軽い計画は平均 T 約 10790、effort 3 は約 10250）。Pacer が選びうる手間 3・5 の経路も sanitizer の下で通った。
- 20261109-030346_final-time-pace: 提出に最も近いビルド clang 18 `-std=gnu++23 -O2 -march=native -stdlib=libc++ -flto=auto -ftrivial-auto-var-init=zero -pthread`（lld がないので既定のリンカ、LOCAL_BENCH なし）、seed 100〜199。WA 0、end_sec 最大 1.720、全注文 effort 0〜2、pace_light 0。
- 20261109-030049_final-time-pace / 20261109-030049_noinit-off / 20261109-030049_final-time-pace-2: NOINIT の読み出し前書き込みの検査。clang libc++、LOCAL_BENCH、env DESIGN_FIXED_ITERS=1（設計を固定反復にして出力を決定的にする）で、(a) zero-init + NOINIT あり、(b) zero-init + NOINIT を空にした写し（`solutions/review-fable1/noinit-off/main.cpp`）、(c) pattern-init + NOINIT あり、を seed 0〜99 で比べた。**100 件すべてで 3 本の出力（紙と全注文の操作列）がバイト単位で一致**。NOINIT の配列が書く前に読まれていれば (a)/(c) はスタックのごみ、(b) は 0 を読むので出力が変わるはずで、一致は読み出し前書き込みがない強い証拠。
