# deval-vselect

改良元: `solutions/argon-des-perf-latew105`。評価関数は `solutions/deval-model` の固定済み V。

窓割当てを共有し、焼きなましの総反復数を複数候補へ分割する。各候補を filler climb、再割当て、穴あけ、穴あけ後の再割当てまで仕上げ、V が最小の設計を使う。注文処理による模擬評価はしない。

既定は候補 2 個。`DEVAL_CANDIDATES` で個数を指定でき、`ANNEAL_ITERS` は候補全体の反復数。候補の乱数 seed は固定 salt 0, 1, ...。`DEVAL_SALT` で先頭 salt を変更できる。その他の段の反復数は改良元と同じ。設計が遅い場合は追加候補を省略する。

このディレクトリは比較実験用でもある。`DEVAL_MODE` は 0 が独立分割、1 が前半共有の分岐、2 が仕上げだけの再始動、3 が途中状態の選択。分岐の `DEVAL_SHARED` は共有する段数、`DEVAL_BRANCH_SCALE` は各分岐での反復数倍率。分岐モードの `ANNEAL_ITERS` は元の全 4 段分の反復数であり、総量は共有段数と分岐数から決まる。

途中状態は `DEVAL_ELITES` 個を進行度 `DEVAL_ELITE_START` 以降で採取する。`DEVAL_ELITE_CURRENT=1` は現在状態、それ以外は各段での目的値最良状態を記録。`DEVAL_ELITE_SAMPLES` 個の積分点による V で事前に絞り、`DEVAL_KEEP_FINAL=1` なら最終状態を必ず仕上げる。`DEVAL_MATCH_ITERS` は穴あけ前の再割当て回数。

`DEVAL_REFINE` は完成状態の unit 入替え試行数。ペアの比較窓での実現可能性、各列の両色、穴あけ済みの位置を保ち、32 点の V が下がる変更を採用する。`DEVAL_REFINE_BATCH` 個の候補を `DEVAL_SCREEN_SAMPLES` 点で絞る実験にも対応。`DEVAL_VMATCH` は Hungarian 法の提案する巡回置換を V で採否判定する反復数、`DEVAL_VMATCH_WEIGHT` は提案用の filler 価値の重み。これらは設計の評価に注文処理を使わない。

`DEVAL_LOCAL_OBJECTIVE` は焼きなましの目的を列単位の 7 項回帰モデルへ近づける混合率（既定 0）。仕上げでは元の目的に戻す。すべての実験設定と run-id は `experiments.jsonl` に記録する。

V は固定した 32 個の Sobol 積分点、列上端色の平均場更新 2 回、142 特徴量の線形結合。積分点は XOR 基底から復元する。評価関数の係数は Task 1 の学習 seed 0–499 で固定したものを使う。

提出時には経過時間 1.72 秒以降の注文を軽量化する。通常計画 1 個を合法性確認して使い、追加の候補探索や後処理を省略する。LOCAL_BENCH ではこの切替を無効にする。保存設計は V で選んだもの。@paper/@ops と既存の診断は維持する。

`dv_candidates` は実際に仕上げた候補数、`dv_chosen` は採用候補、`dv_first` / `dv_best` は V、`dv_anneal_sec` / `dv_finish_sec` / `dv_eval_sec` は各段の候補合計時間。`light_requests` は軽量処理した注文数。

`dv_refine_accepted` は完成状態の入替え採用数、`dv_vmatch_calls` / `dv_vmatch_accepted` は V で評価した巡回置換と採用数。対応する `*_sec` は計算時間。追加探索は設計の経過時間で打ち切る。

`make_source.py` で単独提出可能な main.cpp を再生成する。`run.py` は標準の評価スクリプトを実行し、コンパイルも共有ロック内で行う。
