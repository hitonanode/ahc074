# astra-design

改良元: solutions/imp-s2hd

`main.cpp` は改良元と同一のコピー。提出コードへの変更はない。`Design::Annealer` の候補生成、停滞対策、複合手、差分評価を検討するための計測スクリプトを置く。

目的関数、窓の割り当て、注文処理、`kAnnealEnd=1.305`、`kClimbEnd=1.36`、`CLOCK_SCALE` は改良元と同じ。

`build.py` は計測用コピーだけに `anneal_cost` を追加し、模擬版だけ補助紙の打ち切りを1000秒へ延ばす。提出用の `main.cpp` は変更しない。`reproduce.py --list` で検討した候補の一覧、`reproduce.py <候補名>` でそのソースを復元できる。

計測手順、結果、採否は [REPORT.md](REPORT.md) に記録した。
