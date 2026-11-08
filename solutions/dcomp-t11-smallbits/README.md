改良元: solutions/dcomp-combo-alt1

窓のevaluate_moveでpending（およびClangのvalid）の8 laneのmaskを下位bit順に列挙し、有効な要素だけをstoreする。実要素の昇順・関係費用・目撃cycleの更新順を保つ。従来の0 maskのstoreは実要素の末尾以降だけを書き、その領域は読まれない。

profileではGCCのev_simdが窓の約24%、validが約10%。固定予算・GCC/Clangの既存選択・ログ・profiler・実験スイッチ・目次と段・DesignStoreを保持する。
