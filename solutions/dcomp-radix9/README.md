改良元: solutions/dcomp-hole4

窓探索のmatching_costにある安定2段radix sortの桁分割を8+9 bitから9+8 bitへ変える。17bitの費用と元のpair番号の同点順は同じ。prefix和と2回の安定scatterはそのまま。要求処理・候補・乱数・予算を変更しない。ログ、profiler、実験スイッチ、DesignStoreを維持、時間fallbackなし。
