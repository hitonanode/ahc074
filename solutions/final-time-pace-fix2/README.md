# final-time-pace-fix2（final-time-pace + レビューで見つかった 2 か所の修正）

改良元: `solutions/final-time-pace`。solutions/final-time-pace-fix1 から、3 つ目の修正（設計のやり直しの窓の探索）を外したもの。手元の入力で出力が変わるものはない。

## 修正

1. **shift_byte（後処理の並べ替え）。**
   - p == dest == 191（K − 1）のとき、else 側の `memmove(&o[dest + 1], …, 0)` が、`std::array<uint8_t, 192>` の範囲外の `o[192]` を取っていた（未定義動作）。
   - libc++ の範囲検査つきのビルド（`_LIBCPP_HARDENING_MODE_DEBUG`）では、final-time-pace は全部の seed で止まる（run 20261109-040853_final-time-pace で 200/200）。
   - p == dest は何もしない操作なので、先頭で返すようにした。
2. **samples_for（設計の評価 V の標本点）。**
   - kBasis25 / 31 / 35（[6][H] の表）を `&kBasisXX[0][0]` から 1 本の配列として読んでいた。`basis[(b + 1) * H + j]` は内側の配列の範囲を越える。
   - 2 つの添字で読む小さな関数 `basis(row, j)` にした。値は同じ。

## 外した修正: 設計のやり直し（attempt ≥ 1）の窓の探索

- **何が起こるか:** attempt 0 の初期化に失敗すると、attempt 1（汎用窓 32）が assign_windows をもう一度呼ぶ。そのとき絶対期限はもう過ぎているので、探索は 0 回で終わる。dual30 はここで 160000 回探していた。
- **fix1 の直し方:** その呼び出しの間だけ固定回数に戻し、0.5 秒で打ち切った。
- **外した理由:**
  - 手元の一様乱数の入力では、この道を一度も通らない（時間で決める設計の 2000 seed でも、全部が汎用窓 38 のまま）。
  - 通るのは Astra の作った入力（変わる窓の少ない入力）だけで、そこでは fix1 の方が悪い。
    - スコアは final-time-pace より +4.12 ± 0.66%（0/82/38、run 20261109-043040 と 20261109-040949_final-time-pace）。
    - 探索した汎用窓 32 の割り当ては初期化に失敗しやすく、28 に落ちる。
  - 固定回数だけでは、作った入力で 1 回が約 150 µs と重く、25 秒かかった（run 20261109-040949_final-time-pace-fix1）。探索 0 回の final-time-pace は時間の面で安全。

## 試験用の切り替え（LOCAL_BENCH や試験のビルドだけ。本番のビルドにはない）

- 環境変数 `DESIGN_TEST_FAIL=n`（LOCAL_BENCH）: 最初の n 回の設計を失敗とみなす。
  - 1: 汎用窓 32 でやり直す。
  - 2: 28 でもやり直す。
  - 3: 非常用の設計になる。
- マクロ `NOINIT_EMPTY`: NOINIT（と NOINIT_CLANG）を空にする。`-ftrivial-auto-var-init=pattern` と合わせ、NOINIT を付けた配列を書く前に読む箇所がないかを、出力の一致で確かめるため。

## そのほか

- `submit.cpp`: 提出用のファイル。solutions/dcomp-notes/trim_tool.py で main.cpp を縮めたもので、プリプロセス後のトークン列は main.cpp と同じ。
- `check_submit.py`: submit.cpp と main.cpp を、本番の GCC・Clang のビルドで比べる。比べるのは `-E -P` のトークン列と、`-Wall` の警告。評価のロックの下で動かす。
- `run.py`: flags をそのまま使う評価の補助（solutions/review-astra1/run.py の写し）。`REVIEW_INPUT_DIR` で入力の場所を変えられる。
- 目次と段の目印は改良元のまま。
- GCC の `-Wall` で、final-time-pace になかった `-Warray-bounds` が 1 つ出る。
  - 場所は shift_byte の `o[p]`。修正 1 の先頭の return で経路の分け方が変わり、実際には通らない経路で出る。
  - 実行時の範囲検査では 0 回なので、そのままにした。
