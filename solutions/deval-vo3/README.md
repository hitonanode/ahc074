# deval-vo3

改良元: `solutions/deval-vclean`。

設計段の関数だけ GCC の O3 最適化を有効にする比較実験。fast-math は使わない。Clang は既定の最適化のまま。候補作成、V、固定反復数、時間ガードは親と同じ。コンパイルコマンドは通常どおり C++23 / O2。

再生成: `solutions/deval-vselect/make_o3.py`。
