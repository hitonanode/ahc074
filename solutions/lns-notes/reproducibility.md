# 再現方法

作業ディレクトリはこの worktree。Python は `/home/sato/ahc074/.venv/bin/python`。

- `make_source.py`: helper-wide と各 `.inc` から研究用 `lns-star/main.cpp` を生成する。
- `variant.py NAME --steps ...`: 既定の固定予算を埋めたソース、設定JSON、READMEを新しい `solutions/lns-*` に作る。各試作の `config.json` に全設定がある。評価した厳密なソースは各 run の `src/main.cpp` に残る。
- `run.py`: 標準 `scripts/pahcer_run.py` を呼ぶ。コンパイラにも共通 `flock` と `nice` を付け、ソース・コンパイラ・フラグが一致する成功済みビルドだけ再利用する。実行・保存・記録は標準runnerのまま。
- `replay_batch.py TAG RUN... --seeds A-B`: 保存設計を helper-wide で8列再生し、run対応を TAG.json に記録する。
- `analyze.py BASE RUN... --output FILE`: seedを対応させ、lists1–7 / 全8列 / 実列の手数差とlog比、SE、段の時間と破壊修復の診断を集計する。重い分析は共通 `flock` + `nice` で実行する。
- `structure.py BASE RUN...`: 選択された完成設計で実際に変わった窓と共有ペアを数える。
- `experiment.py`: 凍結ソースで2×/4×/8×予算の同時比較と再生を一式実行する。`LNS_MULTIPLIER=1/3/7` を両研究ソルバへ同時に渡す。時間による探索打ち切りはない。
- `prepare_artifacts.py DIR --source RUN`: 標準runner実行中に保存した候補設計へ出自のメタデータを付ける。候補の再生も `--design-from DIR/candidate-NNN` で標準runnerに渡す。将来の注文を使って設計は選択しない。

## 凍結した主比較

`heldout-frozen.json` に、未見seedを読む前のソースSHA256、設定、凍結日時を記録した。以下を別のTAGで実行すれば、同じ固定予算の通常同時比較・保存・8列再生・対応差の集計を行う。既存のmanifestを上書きしない。

```sh
/home/sato/ahc074/.venv/bin/python solutions/lns-notes/final_grid.py repeat-phase1 \
  --solvers lns-star-study lns-joint-study lns-warm-study lns-full-study \
  --control lns-full-study --budgets 2 4 8 --seeds 500-1000 \
  --baseline 20261108-070629_deval-helper-wide \
  --reason 'Frozen Task7 phase1 reproduction'
```

予算2/4/8は `LNS_MULTIPLIER=1/3/7`。star/joint/warmは5/15/35修復、全再設計対照は既存の8候補パイプラインを1/3/7回追加する。主比較のmanifestが参照する最初の基準 `065042` と、外部負荷を避けた再実行 `070629` は、500件×8列の全出力・全スコア一致を確認済み（`heldout-base-identity.json`）。

最終表は `build_summary.py` で生成する。通常実行の実列スコアと保存設計再生のlist0が全500件一致すること、全スコアが正であること、ソースのSHA256不変を検査する。

```sh
flock -x /home/sato/ahc074/runs/.lock nice -n 10 \
  /home/sato/ahc074/.venv/bin/python solutions/lns-notes/build_summary.py
```

## 候補単位の診断

診断の有効な一覧は `diagnostic-joint-fixed.json` と `diagnostic-star-fixed.json`。修正前の `diagnostic-joint.json` / `diagnostic-star.json` は設計パスの読込に失敗した0点runを含むため使用しない。`run.py` は自分のlns配下のartifactに限り、絶対パスを標準runnerの設計参照メタデータへ渡す。通常のruns配下の参照には手を加えない。

候補0–3は元の4分岐、1000は元の8候補から選んだ設計、2000–2003は各修復の完成候補（3仕上げからV最小を選択）。3000/4000/5000は第1修復の仕上げ前、親の仕上げ前、親の完成後。starとjointで共通の元候補は保存内容の一致を検査して再利用する。`diagnostic_metrics.py` が対応する100訓練seedでVのwithin-case相関、分割半分による信頼性、仕上げ前後の実手数を集計する。診断もすべてhelper-wideの8列再生で、設計中に実注文を評価しない。

主再生の外部負荷警告は `repeat_noisy_replays.py`、候補診断の警告は `repeat_candidate_load.py` で同じ設計と注文列を再実行し、`identity_orders.py` で全出力とスコアの一致を確認する。結果は `clean-replay-checks.json` と `clean-candidate-checks.json`。時間比較には通常の同時compareだけを用いる。

研究版の通常評価は全て `--no-record`。設計読込の再生は標準仕様で記録対象外。1×の不変性確認だけは通常記録する。
