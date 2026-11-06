改良元: `solutions/argon-des-perf-latew105`（分析の入出力は `solutions/deval-seed/analysis` を参考にした）。

設計状態だけから、ランダムな注文列に対する平均操作数を予測する研究用のディレクトリ。提出用の解法は変更しない。

- 訓練とモデル選択は seed 0–499。検証用には原則 seed 400–499 を取り分け、最終的に seed 0–499 で再学習する。
- seed 500–999 は、モデルとパラメータを確定してから一度だけ評価する。
- 書き込み先はこのディレクトリだけ。ビルドと重い分析は `flock -x /home/sato/ahc074/runs/.lock` の下で実行する。
- 実測操作数とラベルは学習の教師としてだけ使う。予測側は DesignState とバーコードから計算し、`Solver::process` は呼ばない。

方法、再現手順、結果、統合への提案は `REPORT.md` に記す。

最終Vの入口は `value.hpp` の `deval::DesignValue::from_design(state)`。`design_features.hpp`、`surrogate.hpp`、`poset_data.hpp`、`quadrature.hpp` と一緒に使う。設計非依存の表を候補間で共有するため、`DesignValue` は1回だけ構築する。

Vは、32点で取っ手の先頭色を平均した被覆DPと、先頭色分布の2回の更新を使う。リセット強度は2、更新の減衰は0.5、fillerの設置・返却の代理費用は1.6。142特徴の線形結合を、操作／注文の単位で返す。全特徴と増分更新の可否は `SPEC.md` に記した。

`complete_training.sh` は保存済みrunからの訓練・検証、`finalize.py` は固定後のテスト評価、`final_cpp.sh` はC++の生成とGCC・Clangでの照合を行う。`bench_*.cpp` は設計評価だけを測る分析用プログラムで、対話型の解法ではない。
