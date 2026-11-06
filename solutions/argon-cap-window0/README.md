改良元: solutions/argon-cap-balance

対照の版。黒と白の比を見ずに、キャップを常に物理窓 0 に置く（入力で窓 0 と窓 63 を入れ替え、出力で戻す）。ほかは argon-cap-balance と同じ。

- バーコードは一様乱数なので、窓 0 と窓 63 は統計的に同じ。argon-des-perf-latew105 との差は、窓を入れ替えて設計の探索の道筋が変わることによるぶれだけになる。
- argon-cap-balance（最も均等な窓）と argon-cap-biased（最も偏った窓）の差が、このぶれより大きいかを判断するために使う。
- stderr の指標: `cap_physical`（常に 0）、`cap_deviation`（窓 0 の |2 × 黒の数 − 256|）、`cap63_deviation`（窓 63 の同じ値）。
