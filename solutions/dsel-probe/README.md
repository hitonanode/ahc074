# 設計の乱数 seed を変える計測用の版（dsel-probe）

改良元: solutions/esw-fixiter

設計の良し悪しが乱数でどれだけぶれるか（PR 115 の「設計選択」がなぜ効くか）を調べるための計測用の版。提出用ではない。

## 変えたこと

- 環境変数 `DESIGN_SALT=s`（0 以外）で、設計の各段の乱数の初期値を変える（splitmix64 で混ぜて元の初期値に XOR）。`s = 0` か未設定なら esw-fixiter と完全に同じ出力。
- `DESIGN_SALT_STAGES`（ビットの和、既定 31 = 全部）で、変える段を選べる: 1 = 比較器の初期化（Comparator::init）、2 = 窓の割り当て（assign_windows）、4 = 設計の焼きなまし（Design の乱数。初期化と焼きなまし、filler climb）、8 = 再割り当て（rematch_probability）、16 = 穴あけ（Perforation）。
- 環境変数は scripts/pahcer_run.py から解法へそのまま渡る（`DESIGN_SALT=3 scripts/pahcer_run.py solutions/dsel-probe ...`）。設計は回数固定なので、別々の評価でも同じ seed なら同じ設計になる。

## stderr の指標

- `design_salt`、`design_salt_stages`: 使った値。ほかは esw-fixiter と同じ。

## 設計の後段の切り替え（計測用、既定は esw-fixiter と同じ）

- `CLIMB_LAMBDA`（既定 1.0）: filler climb の受理で proxy に掛ける重み（`cur − λ × proxy` が下がれば採る）。
- `CLIMB_PROXY_MEAN=1`: filler climb の列の価値を「各色の最も強い資格のある紙の効用」ではなく「各色の紙の効用の平均」にする。
- `RM_ITERS`（既定 4）・`RM_WEIGHT`（既定 1.0）・`RM_STRENGTH`（既定 2.0）: 再割り当て（rematch_probability）の回数、穴埋めの価値の重み、先頭の色の確率のリセットの強さ。
- 回数の上書き `CLIMB_ITERS` などは esw-fixiter のまま使える。
- `FG_SECOND`（既定 0.6）: 設計の filler_gain（filler climb・再割り当ての穴埋めの価値）で、2 窓目を覆うときに引く手数（注文処理の add_filler_demand は esw-ptune で 0.8 にした）。
- `PERF_WEIGHT`（既定 0.5）: 穴あけ（Perforation::run）の穴埋め利益の重み。

## 計測と分析の道具（このディレクトリ。使い方は各ファイルの冒頭）

- `run_salts.sh SEEDS ORDERS SALT...`: 塩ごとに設計を保存（`--save-design`）し、保存した設計を `--design-from --orders` で評価する。`SOL` で解法、`TAG` でコメントを変えられる。出力は「塩 設計の run 評価の run」の行（以下の LIST）。
- `variance.py LIST`: ケースの中で設計 × 注文列の 2 元配置に分け、設計の真の sd、雑音、何設計から選ぶといくら得かを出す。
- `features.py LIST [--labels]`: 設計の stderr の指標とラベル別の手数を、設計の効果とのケース内の相関で並べる。
- `timeline.py LIST`: 設計の差が注文の何番目に出るか。
- `colfix.py LIST`: 列ごとの模型の穴の費用と実際の fix。`mismatch.py`・`colmism.py`・`reqmism.py`: 注文の前の取っ手の色の食い違い。`fillcover.py`: 穴埋め紙 1 枚が覆う穴の数。`pertarget.py`: 2 つの設計の目標ごとの手数。
- `coverage.py`・`proxy.py LIST --seeds A-B`: 保存した設計から穴埋めの覆いの指標と filler climb の proxy を計算し直す。
- `pair_compare.py RUN_A RUN_B ...`: 違う設計を評価した `--orders` の run どうしの、seed ごとの対の差（平均 ± SE）。
