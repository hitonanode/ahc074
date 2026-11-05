# 本流に query-memo と Hungarian の重複計算の削減を入れた版（esw-memo）

改良元: solutions/assign-search

## 改良元からの差分

2 つの版の差分を合わせた（変えた場所は重ならない）。

- **query-memo**（solutions/query-memo、Astra 1）:
  - 目標ごとに、前回効いた補助紙の置き方（1〜2 枚、汎用層の順、差し込み位置）を覚える。
  - 次に同じ目標が来たら、今の積み方から掘り出しと色合わせを計算し直して、計画の候補に加える。
  - 設計固定 2000 件 × 2 本で −0.0028 ± 0.0006%、通常の 2000 件で −0.0033 ± 0.0009%。req_sec +0.5%。
- **design-frame-lazy**（solutions/design-frame-lazy、Astra 2）:
  - Hungarian（先頭を考えた目標の再割り当て）で、直後に同じ状態で行っていた再計算と、使わない単独紙の利益の計算を省く。
  - 出力は同じ。Hungarian は 29.5 → 25.1 ms。
- 設計（紙の模様）は改良元と同じになり、注文の操作だけが query-memo の分だけ変わる。
- 汎用窓の数 G は 38 のまま（G = 37 は差なしで遅い、39 は悪化。trial_log 2026-11-05）。

## スイッチと stderr の指標

- query-memo の `QM_*`（README は solutions/query-memo）と、改良元のスイッチ・指標をすべて引き継ぐ。
