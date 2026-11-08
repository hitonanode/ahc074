改良元: solutions/dcomp-combo-alt1

annealのeval_holesが約150msを占めるため、整数カウントの正確なqf商を表にする。resetは2×整数なのでresetごとに257×257個を元のqfで生成し、全segment・branchで共有する。SIMD除算をAVX2 gatherで置換する。加算順と最終sumはそのまま。

表は使ったresetだけ生成する。最大仮想reserveは約68MB、実際に生成した部分だけ使用。近似・fast-math・時計による切替は使わず、ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。
