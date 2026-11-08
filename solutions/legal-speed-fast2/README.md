# legal-speed-fast2（legal-speed-fast + 次の注文の費用の cache を 4 倍に）

改良元: `solutions/legal-speed-fast`。出力は改良元と同じになるはず（cache は鍵全体を比べるので、当たったときの値は計算し直した値と同じ）。

## 改良元からの差分

- 次の注文の費用（adaptive_next_cost）の cache を 256 から 1024 項目にする。legal-speed-dups の数え方（run 20261108-085843）では、cache に当たらなかった計算 8.9 万回/ケースのうち 14%（1.2 万回）は、同じ注文の中で前に計算した鍵で、場所の取り合いで消えていた。
