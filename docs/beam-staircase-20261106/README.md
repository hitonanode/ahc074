# AHC074 階段・ビーム探索シリーズ（2026-11-06）

研究全体の結論は [report.md](report.md) を参照。研究用ソース4世代とケース別CSV/JSON、実験ノートを収録する。

| 内容 | 場所 |
|---|---|
| 独立64段・残余bitビーム | [solutions/beam-topdown](../../solutions/beam-topdown/) |
| 26段・完成割当ビーム | [solutions/beam-staircase-v1](../../solutions/beam-staircase-v1/) |
| 列容量・ペア・ハンドルの連動最適化 | [solutions/beam-staircase-v2](../../solutions/beam-staircase-v2/) |
| 穴あけと3削除→1修復 | [solutions/beam-staircase-v3](../../solutions/beam-staircase-v3/) |
| 100ケース・追加30ケースの比較表 | [data/](data/) |
| 原実験ノート（初期/v2/v3） | [notes_topdown.md](notes_topdown.md), [notes_v2.md](notes_v2.md), [notes_v3.md](notes_v3.md) |

**注意**: v3は平均約3.66秒で2秒制限を超える。既存の最新提出解を超えたという結果ではなく、GitHub標準2000ケース・同時比較でも未評価。公式Rustテスタによる検証も未実施。
