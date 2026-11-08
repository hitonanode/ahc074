# legal-speed-fast3chk（legal-speed-fast3 の canonicalize の省略を確かめる版）

改良元: `solutions/legal-speed-fast3`。出力は改良元と同じ。提出用ではない。

- 試行の値の計算で、途中から始めた canonicalize の結果（top_d と補助紙の列）を、下から全部たどる canonicalize の結果と比べ、違った回数（と、始めた位置より下が元の並びと違った位置の数）を `canon_mismatch` に、比べた回数を `canon_checked` に出す。
