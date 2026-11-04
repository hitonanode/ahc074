# 穴埋め紙の価値を含めた目的での山登り（jclimb、研究用）

改良元: solutions/dsel-probe（= solutions/esw-fixiter に、設計の乱数の塩 DESIGN_SALT と filler climb の重み CLIMB_LAMBDA の切り替えを足した計測用の版）

## 背景

dsel-probe の計測（trial_log 2026-11-05）で、同じケースの設計どうしの実際の手数の差は、設計の目的（model_cost）よりも、`model_cost − 0.74 × proxy`（proxy は filler climb の「列の先頭の紙の穴埋めの価値」を最終の設計で計算し直したもの）の方がずっとよく説明できた。esw-fixiter の filler climb は同じ形の目的を持つが、動かせるのは「両方の取っ手で色の変わらない同じ種類の 2 単位の列の入れ替え」だけで、回数を 4 倍にしても −0.02% しか変わらない（飽和）。

## 変えたこと

- filler climb の後に、同じ目的（`cur − λ × proxy`）で動きを広げた山登り `Design::jclimb` を足した（既定では行わない。環境変数 `JC_ITERS` で回数を与えたときだけ）。
  - 動き: どの種類の 2 単位の列の入れ替え（新しい列で有効なら色が変わってよい。両方の色の制約は colcost の罰が守る）、1 単位を別の列へ移す（元の列は 2 単位以上残す）、対と別の単位の間で目標を 1 つ交換する（両立する対で、列で有効なもの）。
  - まず模型（update）で値を付け、模型が `λ × JC_SCREEN` より上がるならすぐ戻す。そうでなければ、filler climb と同じく先頭の紙の効用を更新し（色の確率と q は開始時のまま）、`cur − λ × proxy` が下がれば採る。先頭の紙の資格（各色で最も重い単位）は列ごとに数え直す。
- 環境変数: `JC_ITERS`（回数、0 なら行わない）、`JC_LAMBDA`（λ、既定 0.75）、`JC_SCREEN`（既定 2.0）、`JC_MIX=a,b,c`（入れ替え・移動・交換の割合、既定 1,1,1）。dsel-probe の `DESIGN_SALT`・`CLIMB_LAMBDA` もそのまま使える。

## stderr の指標

- `jclimb_iters`、`jclimb_evaluated`（模型の足切りを通った数）、`jclimb_accepted`、種類ごとの採用数 `jclimb_swap`・`jclimb_move`・`jclimb_exchange`、`jclimb_proxy_gain`・`jclimb_cur_change`（1 目標あたり）、`jclimb_end_sec`。
