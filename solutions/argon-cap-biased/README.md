改良元: solutions/argon-cap-balance

argon-cap-balance の選び方を逆にして、256 個のバーコードで黒の数が 128 から最も遠い窓（黒と白が最も偏った窓）をキャップの窓にする。同点なら窓 63、次に番号の小さい窓。ほかは argon-cap-balance と同じ（入力で選んだ窓と窓 63 を入れ替え、出力で戻す）。

- stderr の指標: `cap_physical`（キャップを置いた物理窓）、`cap_deviation`（その窓の |2 × 黒の数 − 256|）、`cap63_deviation`（窓 63 の同じ値）。
