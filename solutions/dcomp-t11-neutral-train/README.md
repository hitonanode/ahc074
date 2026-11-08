改良元: solutions/dcomp-combo-alt1

研究用。中立候補の修復枠を24に広げ、既存のHEAVY_PREDICTで修復前の特徴と修復後の費用を記録する。各roundの直接改善後のincumbent費用も記録し、候補選択の利得を過大に数えない。

seed0–99で順位予測を当てはめ、100–199で予備判定する。研究版は固定設計replayだけで実行し、記録しない。修復数は固定、時計分岐なし。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。
