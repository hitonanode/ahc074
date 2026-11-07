# deval-msd

改良元: solutions/deval-vbranch-o3。

窓割当てのgreedy matchingで、費用キーの上位桁を先に安定分配し、下位桁はgreedyが実際に読むバケットだけを安定挿入ソートする。必要な組数に達した後のバケットを並べ替えない。費用が同じ組の順序とgreedyの選択結果は元の2段radix sortと同じ。探索回数と時間ガードは変えない。
