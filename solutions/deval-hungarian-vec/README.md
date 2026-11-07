# deval-hungarian-vec

改良元: solutions/deval-hungarian（元はdeval-vbranch-o3）。

Hungarian法の距離更新を4列ずつAVX2で計算する。各列の減算順を保ち、最小値の同点では列番号が最小のものを選ぶ。訪問済み列のポテンシャル更新と未確定距離の一括減算も分離する。探索予算・浮動小数点モード・時間ガードは同じ。
