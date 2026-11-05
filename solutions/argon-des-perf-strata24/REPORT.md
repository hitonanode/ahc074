# D2: 層別24標本（時間条件未達）

基準は `solutions/argon-req-completefast-v3`（PR #140）。色標本を8独立標本から24層別標本に変更する。
32標本版の時間を減らすための候補で、ownerの区間DP差分は含めていない。

先頭500件は `20261106-032001_argon-req-completefast-v3` /
`20261106-032053_argon-des-perf-strata24`。差−0.007967 ± 0.009489%、258/16/226。

最終比較は `20261106-032942_argon-req-completefast-v3` /
`20261106-032942_argon-des-perf-strata24`、通常2000件、記録・設計保存あり。

- 差 **−0.020351 ± 0.004741%**、1056/61/883。
- judge平均 **1.580976→1.601483秒**、p99 **1.756089→1.782794秒**。
- judge最大2.373865→2.402144秒、2秒超え2→2件。
- req_sec 0.440647→0.441067、helper_end_sec 0.934865→0.954297、end_sec 1.389355→1.408937秒。
- 穿孔時間10.043→22.560 ms、穴数7.563→6.216。
- 外部負荷平均0.14/最大2.09コア、警告なし。
- WA・self_wrong・op_label_errorsは全件0、4構成のビルド警告0。
  `build-results.json` / `final-audit.json` に照合結果を保存した。ビルド用実行ファイルは削除済み。

**得点は改善したが、時間枠を満たさないため不採用。**
同時比較で時間枠を満たした32標本＋owner DP差分の `argon-des-perf-stratacut` をマージ対象とした。
穿孔単体は24標本の方が速いが、全体時間では逆になっている。
標本数の効果をこの全体時間差だけから一般化しない。
全検討は[調査REPORT](../argon-des-perf-neighborhood/REPORT.md)、全数値は[MEASUREMENTS](../argon-des-perf-neighborhood/MEASUREMENTS.md)。
