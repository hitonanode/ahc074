# D2 旧基準上の採用条件確認: 層別32標本による穿孔

改良元は `solutions/argon-des-perf-gaincache`（PR #139）。
外部助言01-1「穿孔処理とフィラー評価の対象拡大」の継続検証から得た変更。
詳細な比較・失敗案・診断は [調査REPORT](../argon-des-perf-neighborhood/REPORT.md)、
全runの時間は [MEASUREMENTS](../argon-des-perf-neighborhood/MEASUREMENTS.md)。

`Handle perforation` の `Perforation::rebuild` が使う8個の独立色標本を、32個の層別標本へ変更する。
各目標・列で等分した区間から抽出して独立に並べ替える。受理係数0.7、owner条件付け、利益上限、
不変なDPキャッシュの再利用は維持する。色標本の選択誤差を抑え、回収しにくい穴が減る。
変更は+11/−4行。他の段、段の目印と目次、全ログ・profiler・switchは不変。

基準 `20261106-021800_argon-des-perf-gaincache`、候補 `20261106-021800_argon-des-perf-strata32`。
通常2000件、両側設計保存、記録あり。

- **-0.021836 ± 0.004853%**、勝/分/敗 **1039/58/903**、4.50 SE。
- judge平均 **1.557420→1.582414秒**、p99 **1.727111→1.747722秒**。
- judge最大 1.813275→1.853089秒、2秒超え0→0。
- req_sec 0.424729→0.427495、helper_end_sec 0.933146→0.953637秒。
- 追加時間当たり **0.874%/秒**、平均穴数 7.563→6.114。
- WA・self_wrong・op_label_errors全件0。GCC/Clang × LOCAL_BENCH有無で警告0。
- 外部負荷に警告なし。`build-results.json` / `final-audit.json` でソースと検証物を照合。
  ビルド用バイナリは/tmpに作り、削除した。

この版はPR #139に対する採用条件を満たしたが、最終確認時にBASEがPR #140へ更新された。
マージ対象は後続の `argon-des-perf-strata32-v2` で再判定する。
層別化だけの効果と独立32標本との差は有意ではないため、改善全体を層別化だけに帰属させない。
D2は未完了で、より安い標本数や新しい動作点での残る候補は再開後に扱う。D3〜D5は未開始。
