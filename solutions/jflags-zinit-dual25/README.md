# jflags-zinit-dual25（dual25 + ジャッジの zero-init で埋められる局所の配列を初期化しない）

改良元: `solutions/dcomp-combo-dual25`。手元のビルド（zero-init なし）の出力と速さは改良元と同じ。

## 改良元からの差分

- ジャッジは `-ftrivial-auto-var-init=zero` でビルドする。初期化子のない自動変数は、関数に入るたびに 0 で埋められる。
- マクロ `NOINIT`（Clang は `[[clang::uninitialized]]`、GCC 12 以降は `__attribute__((uninitialized))`、ほかは空）を作った。Clang の `-Rpass-missed=annotation-remarks` で 0 埋めが入る場所を調べ、そのうち頻繁に呼ばれる作業用の配列に付けた。
  - 付けたのは、書いてから読む配列だけ（数と一緒に使うバッファや、使う範囲を先に埋める配列）。
  - 付けた場所: 窓の割り当て（move の評価の作業域、elite の候補）、設計の焼きなましの multi_move、確率の勾配、canonicalize、次の注文の費用（鍵と作業配列）、adaptive_insert、post_optimize の再生、eject と 2 対 2 の書き換えの作業域、付け替えの候補、列の上端の表、鎖の候補。
- 窓の割り当ての 4 つの作業域（af / ar / bf / br）は、`NOINIT_CLANG`（Clang だけ）にした。GCC ではそこに付けると、窓の割り当てが遅くなった。
- `from-dual25.patch` は改良元からの差分。兄弟の版にも `git apply --3way` か `patch -p1` で当てられる（dual30 で確かめた）。
