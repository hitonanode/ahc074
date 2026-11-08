# final-time-pace-fix1（final-time-pace + レビューで見つかった 3 か所の修正）

改良元: `solutions/final-time-pace`。2 つのレビュー（solutions/review-astra1、solutions/review-fable1）の指摘のうち、コーディネーターが確かめた 3 つを直した。手元の入力で出力が変わるものはない。

## 修正

1. **shift_byte（後処理の並べ替え）。**
   - p == dest == 191（K − 1）のとき、else 側の `memmove(&o[dest + 1], …, 0)` が、`std::array<uint8_t, 192>` の範囲外の `o[192]` を取っていた（未定義動作）。
   - libc++ の範囲検査つきのビルド（`_LIBCPP_HARDENING_MODE_DEBUG`）では、全部の seed で止まる（Astra の run 20261109-031300）。
   - p == dest は何もしない操作なので、先頭で返すようにした。出力は変わらない。
2. **samples_for（設計の評価 V の標本点）。**
   - kBasis25 / 31 / 35（[6][H] の表）を `&kBasisXX[0][0]` から 1 本の配列として読んでいた。`basis[(b + 1) * H + j]` は内側の配列の範囲を越える。
   - 2 つの添字で読む小さな関数 `basis(row, j)` にした。値は同じ。
3. **設計のやり直し（attempt ≥ 1）の窓の探索。**
   - attempt 0 の初期化に失敗すると、attempt 1（汎用窓 32）が assign_windows をもう一度呼ぶ。
   - そのとき map_search と gopt の絶対期限はもう過ぎているので、探索は 0 回で、初期の割り当てのまま進んでいた。dual30 はここで kMapRetryIters = 160000 回探していた。
   - attempt ≥ 1 の呼び出しの間だけ `design_time.active` を false にして、dual30 と同じ固定回数を探すようにした。直後に元に戻す。
   - ただし、この探索は kMapRetrySeconds（0.5 秒、倍率込みの時計）で打ち切る。
     - ふつうの入力では、160000 回は約 0.30 秒で終わる。手元の重い負荷の下では 0.5 秒近くかかることがある（DESIGN_TEST_FAIL の試験）。
     - 変わる窓の少ない入力（Astra の作った入力）では 1 回が約 100 倍重い。固定回数だけだと 25 秒かかった（run 20261109-040949）。
   - attempt 0 はそのまま。後の段は自分の期限を保つ。
   - 手元の 2000 seed では、この道は一度も通らない（時間で決める設計の 2000 seed でも、全部が汎用窓 38 のまま）。

## 試験用の切り替え（LOCAL_BENCH や試験のビルドだけ）

- 環境変数 `DESIGN_TEST_FAIL=n`（LOCAL_BENCH）: 最初の n 回の設計を失敗とみなす。
  - 1: 汎用窓 32 でやり直す。
  - 2: 28 でもやり直す。
  - 3: 非常用の設計になる。
- マクロ `NOINIT_EMPTY`: NOINIT（と NOINIT_CLANG）を空にする。
  - `-ftrivial-auto-var-init=pattern` と合わせ、NOINIT を付けた配列を書く前に読む箇所がないかを、出力の一致で確かめるため。
- `run.py`: flags をそのまま使う評価の補助（solutions/review-astra1/run.py の写し）。`REVIEW_INPUT_DIR` で入力の場所を変えられる。

## そのほか

- `submit.cpp`: 提出用のファイル。solutions/dcomp-notes/trim_tool.py で main.cpp を縮めたもので、プリプロセス後のトークン列は main.cpp と同じ。
- `check_submit.py`: submit.cpp と main.cpp を、本番の GCC・Clang のビルドで比べる。比べるのは `-E -P` のトークン列と、`-Wall` の警告。評価のロックの下で動かす。
- 目次と段の目印は改良元のまま。
