# jflags-portable-dual25（dual25 の std::sort と std::shuffle を、ライブラリによらない libstdc++ の手順に）

改良元: `solutions/dcomp-combo-dual25`。libstdc++ でビルドしたときの出力は改良元と同じになるはず。libc++ でビルドしても同じ出力になるかを確かめるための版。

## 改良元からの差分

- std::sort は等しい要素の順を、std::shuffle は並べ替えの選び方を、標準ライブラリの実装に任せている。そのため、libc++ でビルドすると（ジャッジの Clang）、手元の libstdc++ のビルドと違う設計や計画を選びうる。
- 12 か所の `std::sort` と 3 か所の `std::shuffle` を、`stdx::sort` と `stdx::shuffle` にした。
  - `stdx::sort` は libstdc++ 13 の introsort と同じ手順（3 点の中央値、番兵なしの分割、深さ 2 log2 n で heapsort、閾値 16 の最後の挿入整列）。
  - `stdx::shuffle` は libstdc++ 13 の std::mt19937_64 での shuffle と同じ手順（2 つの交換位置を 1 回の一様な乱数から取る、Lemire の割り算のほぼない縮小）。
  - どちらも段の目印「Common: library-independent sort and shuffle」の下にある。
- std::stable_sort は結果が一意に決まるので変えていない。ほかは改良元と同じ。
