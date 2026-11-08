# jflags-portable-fp-dual25（jflags-portable-dual25 + どのビルドでも浮動小数の縮約をしない）

改良元: `solutions/jflags-portable-dual25`（dual25 の std::sort・std::shuffle を libstdc++ と同じ手順にした版）。手元の評価のビルド（`g++ -std=c++23 -O2`）と出力が同じになるはず。ジャッジのビルド（`-march=native` つきの GCC、libc++ と zero-init つきの Clang）でも同じ出力になるかを確かめるための版。

## 改良元からの差分

- ファイルの初めで、浮動小数の縮約（a * b + c を FMA 1 命令にする）を切る。Clang は `#pragma clang fp contract(off)`、GCC は `#pragma GCC optimize("fp-contract=off")`。段の目印は「Common: no floating-point contraction in any build」。
- 理由: `-march=native` があると、GCC（既定 -ffp-contract=fast）も Clang（既定 on）も FMA で丸め方が変わる。手元の評価のビルドは -march=native なしで FMA がないので、ジャッジのビルドとは設計から違う結果になる。
