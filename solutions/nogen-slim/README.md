# nogen-slim

改良元: solutions/nogen-payload-col95

- 行頭の字下げを半分（4 文字 → 2 文字）にしただけで、コードは変えていない。
  - 改良元の main.cpp は 561,996 バイトで、AtCoder のソースの長さの上限 512 KiB（524,288 バイト）を超えていた。
  - この版は 502,859 バイト。
- 出力は改良元と同じ。g++（`-std=c++23 -O2 -DCLOCK_SCALE=1.1 -DLOCAL_BENCH` と `-std=gnu++23 -O2`）と clang++（`-std=c++23 -O2`）で、オブジェクトファイルがバイト単位で一致した。
  - 行の数と行番号は変えていないので、`__LINE__` を使う assert の文字列も変わらない。
- 設計を固定した比較には、改良元の run `20261106-141540_nogen-payload-col95` の設計がそのまま使える。
- 解法の説明・パラメータ・stderr の指標は solutions/nogen-payload-col95 の README と REPORT.md のとおり。
