改良元: solutions/dcomp-combo-alt1

next_costの列内scanで、その列に印刷される全ての色の最初の深さが既に分かったら、残りの紙でfirst配列を検査しない。各紙の費用加算とMDP符号化は順番も回数も元と同じ。色が列から全て取り出されている場合は旧検査を最後まで行う。

profileの列内scanを対象にする。近似・fast-math・時計分岐は使わない。予算、ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。
