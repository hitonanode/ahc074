# deval-vdiag

改良元: `solutions/deval-vtarget2`。研究用（診断）。

焼きなましの V の代わりの指標（`DEVAL_VANNEAL=1`、深さごとの吸収率）が、V の取っ手の手数を本当に表しているかを確かめるための値を、stderr に `#vbdiag` の行で出す。設計そのものは改良元と同じ。

- `#vbdiag refresh P V raw fix fill fdig S`: 吸収率を計算し直した直後。
  - P: 新しい吸収率での代わりの指標の取っ手の費用（1 注文あたり）。
  - V: 同じ設計での V の取っ手の手数 (0.871 fix + 1.348 fill + 1.054 fdig) / 0.940。
  - raw / fix / fill / fdig: V の被覆 DP の不一致・色直し・フィラー・フィラーの掘り出し。
  - S: 焼きなましの今の取っ手の費用。
- `#vbdiag end i P S`: 分岐 i の焼きなましの終わり（仕上げの前）。最後の吸収率での代わりの指標 P と、今の取っ手の費用 S。直後に、その設計で計算し直した `#vbdiag refresh` の行が続く（その V が分岐の終わりの V の取っ手の手数）。
