改良元: solutions/esw-slim

D2の設計段の拡張。穿孔処理は基準と同じ。
filler_climbとProbabilityHeadのフィラー効用を、列・色ごとの第1候補と第2候補の混合にする。
順位は頻度、次にフィラー効用。第2候補への確率はARGON_D2_HEAD_RATE（既定0.0625）。
Hungarianの効用の勾配にも同じ混合を入れ、全紙の効用を更新する。
保存出力の列頭の観測頻度を参考にした全ケース共通の定数で、未来の注文は読まない。

指標と予算スイッチは基準と同じ。proxy_before/afterとmatch_decreaseは混合目的の値になる。
既存ログ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を維持する。
検証の記録はsolutions/argon-des-perforation/REPORT.md。
