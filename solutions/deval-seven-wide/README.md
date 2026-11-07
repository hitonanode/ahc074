# deval-seven-wide

改良元: solutions/deval-chain-seven（設計・注文処理の基準はdeval-vbranch-nofb）。

7完成候補の設計を保ち、neutral rewriteで保持する候補幅を2から3へ増やす。固定で計7完成候補を比較する。すべてのケースで同じ回数を使い、時間で減らさない。

最初の4分岐は焼きなまし前半2段を共有し、各分岐をclimb50k・再割当て2回・穴あけ8サンプル・最終再割当てまで完成させる。その後は最良完成配置を起点に、固定saltを変えたclimb25k・再割当て1回・穴あけ・最終再割当てを3回行う。完成V16が改善した場合だけ次の開始配置も更新する。元の4候補を含め最小Vの設計を選ぶ。物理的な穴は仕上げごとに作り直す。

窓割当て450k、窓climb133k、焼きなまし約11.2MとV16の係数は基準と同じ。HungarianのAVX2化、穴あけ整数DPと差分更新、短いfiller列の内部保持、列の連続区間走査、仕上げの確率・被覆情報の共有を使う。GCCではSolverもO3、Clangは既定の最適化を使い、fast-mathは使わない。

注文探索は固定でREPEAT_MIN=0.05、POST_CANDIDATES=5、NEUTRAL_WIDTH=3。F3_*は実験用の上書き。時間不足による軽い注文処理、設計段の時間上限、候補打切りは含めない。DesignStoreは採用した完成設計を保存する。ログ、@paper/@ops、目次・段の目印を維持する。dv_candidatesは完成数、dv_chosenは採用番号、dv_*_secは全候補の合計時間。
