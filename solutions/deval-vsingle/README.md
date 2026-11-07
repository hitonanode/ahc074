# deval-vsingle

改良元: `solutions/deval-vanneal`。研究用。

改良元と同じだが、候補の数と各分岐の反復の割合を環境変数で変えられる。改良元（と deval-vbranch-o3）では 4 と 1/4 が定数だった。

- `DEVAL_CANDIDATES`: 候補の数（既定 4）。
- `DEVAL_BRANCH_SCALE`: 各分岐の反復の割合（既定 1 / 候補の数）。
- `DEVAL_CANDIDATES=1 DEVAL_BRANCH_SCALE=1` で、焼きなまし 1 本（分岐なし、V による選択なし）。`ANNEAL_ITERS` で反復の総数を変えられる。

V の代わりの指標（`DEVAL_VANNEAL`）などは改良元の README を参照。
