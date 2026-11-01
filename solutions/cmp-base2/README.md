# cmp-base2

改良元: solutions/cmp-base（途中の版 cmp-gx 〜 cmp-fast4 をまとめ、コメントを直したもの。今後のベース）

アルゴリズムは cmp-fast4 と同じ（割り当て・その山登り・焼きなまし・穴埋めの山登りを同じ回数にすると出力が一致する。cmp-base/eqcheck.py に `GOPT_STEPS=1500` を付けて seed 0〜47 で確認）。cmp-base からの差分は次のとおり（各版の README と trial_log の「cmp-base の改善（cmp-）」に数字がある）。

- 汎用層の手数の見積り（cmp-gx）: 設計で対の汎用層の費用に使う gcost を、乱数 8 通りの順序からの計画の長さの平均から、720 通りすべての順序からの正確な平均最少手数（M − 最長共通部分列の表、閉包ごとにメモ化）にした。
- 係数と時間（cmp-tune）: ハンドルの穴の重み 0.50 → 0.40、列の外に残す紙の費用 0.8 → 0.6、終わりの状態の重み 0.6 → 1.0。焼きなましを 1.28 秒、穴埋めの山登りを 1.33 秒まで、軽量処理は 1.80 秒から（倍率込みの壁時計）。
- 割り当て（cmp-cut、cmp-gobj、cmp-gobjr2）: 目的に数える対を距離 28 以下から 26 以下に（同じ時間で反復約 2 倍）。割り当ての焼きなましを 0.45 秒まで、そのあと 0.55 秒まで gobj の山登り（両立する近い対を「ハンドル窓の違い + 0.5 ×（閉包の関係の数 − 6）」の小さい順に貪欲にマッチングした 70 組の平均が増えない手を受理）。手の生成・適用・取り消しを焼きなましと山登りで共有。
- 緊急設計の閾値（cmp-gobjr2）: 初期化の打ち切り 0.90 → 1.20 秒、緊急設計への切り替え 0.85 → 1.15 秒、焼きなましの前の 1.05 秒の判定を削除（移植元の閾値は、割り当ての後の初期化の終わり（最大 0.8 秒台）に近すぎた）。
- 焼きなましの速さと近傍（cmp-fast、cmp-fast2、cmp-hswap、cmp-hswap2、cmp-fast4）: 却下した手は保存した数を書き戻して戻す。列だけが変わる手は、穴になるかが変わるハンドルだけを数え直す（move_col）。列の費用をキャッシュ。ハンドルの順の交換は、列 < a と ≥ b の単位にとって h_a と h_b の穴が入れ替わるだけなので、列 a..b−1 の単位と列 a, b の単位だけを見て評価し（列ごとの単位の表を持つ）、率を 0.5% から 15% に上げた（これが最も効いた）。割り当てでは、関係の変わらない対の閉包を計算し直さず、目標ごとの pow をキャッシュ。
- 実験用の切り替え: 環境変数 `MAP_ITERS` / `GOPT_STEPS` / `ANNEAL_ITERS` / `CLIMB_ITERS`（回数固定。GOPT_STEPS と CLIMB_ITERS は −1 でなし）、`-DSIM_HARNESS`（`SIM_SEQS=n` で乱数の注文列 n 本を模擬して平均手数を出す）、`-DFORCE_FAST_MODE` / `-DFORCE_EMERGENCY_DESIGN`。
- stderr: `gobj_before` / `gobj_after` / `gopt_steps`（割り当ての山登り）、`map_iters`、`map_end_sec`（初期化の終わり）、`anneal_iters`、`anneal_end_sec`、`climb_iters`、`climb_accepted`、`proxy_before` / `proxy_after`、`climb_end_sec`、`self_wrong`、`generic_moves`、`total_moves`、`G`、`plan_failures`、`fast_requests`、`req_sec`、`end_sec`。
