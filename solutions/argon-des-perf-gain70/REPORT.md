# 穿孔利益の係数0.7: 得点は改善したが、この版は採用しない

基準は `solutions/argon-des-perf-condbound`（PR #138）。
`design_papers: handle perforation` の `perforation.run(0.5)` を `perforation.run(0.7)` に変えた1行のみ。
調査全体は [D2続きの報告](../argon-des-perf-variance/REPORT.md)。

通常2000件、設計保存つきの2回の比較で得点は同じ:
**−0.022316 ± 0.004631%**、勝/分/敗 **1058/78/864**、平均10328.84→10326.53。
WA・self_wrong・op_label_errorsは0。GCC/Clang、LOCAL_BENCH有無の4構成で警告0。
ビルド確認の実行ファイルは/tmpの一時ディレクトリで作成し、削除済み。

| run-id接頭辞（各々 _argon-des-perf-condbound / _argon-des-perf-gain70） | judge平均 基準→候補 | p99 基準→候補 | 最大 基準→候補 | >2秒 基準→候補 |
|---|---:|---:|---:|---:|
| 20261106-013720 | 1.57253→1.58501 | 1.79596→1.79551 | 2.04872→2.24232 | 1→1 |
| 20261106-014418 | 1.57138→1.58956 | 1.76125→1.80404 | 1.85569→1.95131 | 0→0 |

後者のreq_sec 0.425895→0.428868、helper_end_sec 0.944968→0.958134秒。
追加judge平均0.01818秒に対し約1.23%/秒と費用対効果はあるが、p99≤1.770秒を満たさない。
このため単純な係数変更版は採用せず、同じ設計を作るDPキャッシュ再利用版
`solutions/argon-des-perf-gaincache`を検証する。

この版のソース差と保存出力・4ビルドのSHAは`final-audit.json`で照合済み。
全既存のログ・プロファイラ・スイッチ・DesignStore・CLOCK_SCALE・LOCAL_BENCH・段の目印を保持した。
