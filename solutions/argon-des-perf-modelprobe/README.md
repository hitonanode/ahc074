改良元: solutions/argon-des-perf-latew105

保存設計専用の計測版。--design-fromとともにpahcer_run.pyから実行する。
解法の出力を変えず、128層化標本でフィラー価値を3種類に分けて測る。
d2_probe_sumは解析式のhead価値の和、intervalは重ならない区間の最良和、
unrestrictedは各列の最良区間の無制約和、oneは最良区間1個だけの値。
overlapはunrestricted−interval。holeは既存の穴費用モデル、全て手/注文。
d2_probe_samplesは標本数、d2_probe_secは計測時間。
初期の穿孔は既定32標本のまま。ログ・スイッチ・プロファイラ・DesignStoreを保持する。
main: design model probeの段と目次項目を追加する。
