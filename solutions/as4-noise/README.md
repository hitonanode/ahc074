# as4-noise

改良元: solutions/astra-search4

窓の割り当てで停滞したときに進む候補の選び方に、0.1 幅の決定的なハッシュの揺らぎを加える（同じ費用付近の候補から毎回同じものを選ばないように）。

Astra の試作 noise100（solutions/astra-search4/REPORT.md の 4 章）を、採用版の上に solutions/astra-search4/variants.py の生成関数で重ねたもの。
