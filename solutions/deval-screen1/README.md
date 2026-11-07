# deval-screen1

改良元: solutions/deval-vbranch-o3。

同じ4分岐を filler climb と2回の再割当てまで仕上げ、穴あけ前のVで順位をつける。上位1候補だけ穴あけと穴あけ後再割当てを行い、最後にVで選ぶ。探索回数・温度は元のまま。追加候補は1.12秒を超えたら止め、最初の完成設計を必ず確保する。提出時の時間ガード、LOCAL_BENCHの固定注文予算、DesignStore、診断を維持。
