# deval-vbranch

改良元: `solutions/argon-des-perf-latew105`。実装上は `deval-vreheat` の訓練実験から設定を固定した候補。

窓割当てを共有し、焼きなましの前半2段を1回、後半2段を4分岐する。後半は各1/4の反復数で、合計反復数はSOTAとほぼ同じ。候補0は元の温度、候補1–3は分岐直後を2倍にし、終端までに元の温度へ戻す。

各候補を filler climb 50,000回、再割当て2回、穴あけ、穴あけ後の再割当てまで仕上げる。設計だけから平均操作数を予測するV16で最良候補を選ぶ。Vは対象別の固定積分点、解析的な不一致数補正、先頭色分布の2回更新を使う。係数の学習はseed 0–499。注文処理は呼ばない。Vの汎用紙の期待費用表は窓割当ての厳密表と共有する。

設計経過1.12秒以降は追加候補を開始しない。提出時は残注文の比率をqとして、1.84−0.12q秒から中立探索を省き、1.90−0.30q秒から最初の合法な通常計画を使う。注文処理の軽量化はLOCAL_BENCHでは無効。CLOCK_SCALE、@paper/@ops、DesignStoreと段の目印を維持し、選択済みの設計を保存する。

`dv_candidates`は完成した候補数、`dv_chosen`は選択した候補番号、`dv_first`と`dv_best`は予測操作数、`dv_anneal_sec`・`dv_finish_sec`・`dv_eval_sec`は候補全体の各段の時間。`light_requests`・`hard_light_requests`は提出時の軽量処理の注文数。

再生成の入力と設定は `FROZEN.json`。生成スクリプトは `../deval-vselect/finalize.py`。実験・比較の集計は同ディレクトリの `analyze.py` と `summarize_final.py` を使う。
