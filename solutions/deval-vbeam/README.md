# deval-vbeam

改良元: `solutions/deval-vtarget`。焼きなまし途中の状態を安く選別するモデルを追加する。

既定では最初の 2 段を共有し、後半 2 段を 4 通りの乱数 salt で分岐する。各分岐の反復数は元の 1/4 で、合計反復数は SOTA と同じ。各分岐から途中の現在状態 8 個と目的値最良の最終状態を集める。

各状態を列・穴・ペアなどの静的特徴と先頭 filler の解析的価値で順位付けし、上位 2 個を仕上げる。選別器は seed 0–399 で学習し、400–499 で検証した後、0–499 で再推定。入力は設計状態だけで、将来の注文や焼きなましの進行度を使わない。最終的には対象ごとの積分点と解析的な補正を使う V16 で選ぶ。

`DEVAL_BRANCHES` は分岐数、`DEVAL_SHARED` は共有段数、`DEVAL_BRANCH_SCALE` は分岐の反復数倍率。`DEVAL_CANDIDATES` は仕上げる候補数。`DEVAL_ELITES` は分岐ごとの途中状態数。通常の段の反復数は親と同じ。

設計が遅い場合は追加候補を省略する。提出時は 1.72 秒から軽量リクエスト処理に切り替える（LOCAL_BENCH では無効）。DesignStore と @paper/@ops を維持する。生成は `solutions/deval-vselect/make_beam.py`、選別器は `prescreen.json`。
