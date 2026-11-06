# deval-vbranch-o3

改良元: `solutions/argon-des-perf-latew105`。実装と設定は `deval-vreheat` で検証した4分岐を整理したもの。

窓割当てと焼きなましの前半2段を共有し、後半2段を4候補へ分岐する。各分岐の反復数は元の1/4で、総反復数はSOTAとほぼ同じ。候補0は元の温度、候補1–3は分岐直後の温度を2倍にし、最後には元の温度へ戻す。

各候補を filler climb 50,000回、再割当て2回、穴あけ、穴あけ後の再割当てまで仕上げ、設計だけから平均操作数を予測するV16で選ぶ。Vは対象別の固定積分点、解析的な不一致数補正、先頭色分布の2回更新を使う。係数はseed 0–499で学習。注文処理の模擬は行わない。

Vの汎用紙の厳密期待費用表を窓割当てと共有し、積分点は短いXOR基底から復元する。未使用の候補生成や途中状態の保存は除いた。GCCでは設計を中心とする関数群と共有のComparator・Interleave・ColumnMDP関数をO3で最適化する。Solver本体はこの指定から外す。fast-mathは使わず、Clangでは既定の最適化のまま。

追加候補は設計経過1.12秒以降に開始しない。提出時は窓探索0.85秒、窓climb0.90秒、設計anneal1.15秒、filler climb1.25秒を緊急打切りの目安にする。各段は既存の最良状態への復元を通る。残注文の比率をqとして1.84−0.12q秒から中立探索を省き、1.90−0.30q秒から最初の合法な通常計画を使う。緊急打切りと注文軽量化はLOCAL_BENCHでは無効。

CLOCK_SCALE、@paper/@ops、段の目印、DesignStoreを維持し、選択済みの設計を保存する。`dv_candidates`は完成候補数、`dv_chosen`は採用候補、`dv_first` / `dv_best`は予測操作数、`dv_anneal_sec` / `dv_finish_sec` / `dv_eval_sec`は候補全体の各段の時間。`light_requests` / `hard_light_requests`は提出時の軽量処理の注文数。

再生成の入力と設定は `FROZEN.json`。`../deval-vselect/finalize.py` の `--share-table --prune-branch --o3-design` で生成する。標準評価をビルドのflock付きで呼ぶのは同ディレクトリの `run.py`、最終評価一式は `final_run.py`。
