# deval-vpipeline

改良元: `solutions/deval-vclean`。

前半 2 段を共有し、後半 2 段を 8 分岐（各 1/8 の反復数）する。全 8 候補に filler climb 50,000 回と再割当て 1 回を実施し、穴あけ前の完成した紙を V16 で評価する。上位 2 候補だけ再割当てをもう 1 回、穴あけ、最終再割当てまで実施し、再度 V16 で選ぶ。焼きなましの合計反復数は SOTA と同じ。

途中選別に実際の注文処理は使わない。候補数は `DEVAL_BRANCHES`、最終候補数は `DEVAL_CANDIDATES`。前半の仕上げは経過 1.08 秒で追加を止め、最終候補は 1.12 秒で追加を止める。提出時の注文処理の時間ガード、保存形式、既存診断は親と同じ。

生成は `solutions/deval-vselect/make_pipeline.py`。
