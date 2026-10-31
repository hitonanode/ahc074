# cmp-base

改良元: solutions/cmp-climb

cmp-climb（gpt6pro-06-01-comparator の設計を時間制にし filler_climb を足したもの）を、アルゴリズムを変えずに書き直した版（1976 行の詰めた書き方、clang-format で整形すると 2424 行 → 2352 行、うちコメント 232 行。今後の新しい解法のベース）。構造と主要な関数の役割は main.cpp の冒頭のコメントにある。

- アルゴリズムは gpt6pro-06（比較符号の汎用層 6 枚・汎用窓 36・ハンドル 28、列内の適応的な挿入位置）のまま。時間の管理は clean-base 式: 時計はプログラム開始からの壁時計に `CLOCK_SCALE` を掛けた `elapsed_sec()` だけを使い、割り当ては 0.45 秒、焼きなましは 1.10 秒、山登りは 1.15 秒まで。stderr の指標も clean-base の名前（`anneal_iters`、`anneal_end_sec`、`climb_iters`、`climb_end_sec`、`total_moves`、`generic_moves`、`self_wrong`、`req_sec`、`end_sec`）にそろえた。
- 動作の変更（時間で打ち切るときだけ）: gpt6pro-06 は注文処理中にプロセスの CPU 時間が 1.55 秒を超えたら軽量処理に切り替えていたが、同じ壁時計で 1.70 秒を超えたら切り替えるようにした（通常は 1.4 秒前後で終わるので働かない、遅いマシンへの安全網）。時計の起点がプログラム開始になった（元は main の開始）。
- 削ったもの: 移植元が clean-base 系から引き継いでいて使っていなかったもの（反転ブロックの Block / touch / pair_codes、units / members / color_at、持続の多数派の色 bias_c / bias_g と tops_penalty、巡回順の cyc / init_cycles、常に −1 だった巡回順の前任 top_pred / Filler::pred）、設計側の常に偽だった guardDesign の分岐と係数 1 の digWeight、hole_probabilities、閉路の罰（係数 0 で常に 1 倍）、3 か所に重複していた include、実験用の環境変数（MAP_SEED / MAP_GW など。cmp-time / cmp-climb の README）と gobj の計算。
- 書き換え: 2 つの xorshift を 1 つの型（`mod` と `below` の 2 通りの写像）に、計画の選択肢の列挙を簡単に（古い穴埋め紙がないときは選択肢が同じになるので 1 つずつ）。clean-base の計画探索の説明コメントを、適応的な列に合わせて書き直して戻した。
- 残した切り替え: 環境変数 `MAP_ITERS` / `ANNEAL_ITERS` / `CLIMB_ITERS`（回数固定。CLIMB_ITERS = −1 で山登りなし）、`-DSIM_HARNESS`（`SIM_SEQS=n` で乱数の注文列 n 本を模擬して平均手数を出して終わる）、`-DFORCE_FAST_MODE` / `-DFORCE_EMERGENCY_DESIGN`（安全網の確認用）。
- 出力の一致: eqcheck.py（回数固定でテスター経由、stdout を seed ごとに比較）で、割り当て 1200 回・焼きなまし 100 万回・山登り 2 万回の seed 0〜47、2400 回・200 万回・3 万回の seed 0〜95、4000 回・400 万回・6 万回の seed 96〜159 で cmp-climb と全件一致。g++ / clang++ の `-Wall -Wextra` で警告なし。
- 速さの注意: ハンドルの穴の費用 4xy/(x+y) を、静的な std::array の表から直接の割り算や std::vector の表に替えると、焼きなましが 10〜35% 遅くなった（元の std::array に戻した）。
