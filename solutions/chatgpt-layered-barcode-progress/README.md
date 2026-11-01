# chatgpt-layered-barcode-progress

改良元: [solutions/imp-post](../imp-post/)（`imp-910` と同じコードではない）。**進捗共有用の再構成実装であり、merge / 即提出は意図しない。**

## 変更したこと

- **補助紙の順次回収**: 以前は全補助紙が同時に可視であることを要求していた。上から見える紙を先に戻すと別の紙が見える場合も受理し、実際の返却でもその時点で可視の紙を選ぶ。設計済みの列・取っ手構造に依存する。途中で合法な返却が見つからなければ計画を失敗にする。
- **汎用6枚の順序を選ぶ**: 最下段の不可視紙を動かせない有向状態グラフの全点対最短距離と、各商品に必要な半順序を満たす順序への期待最短距離 `future_value[s]` を作る。現在の要求への最短手数が同じときに将来距離の小さい到達順序を選ぶ。
- **後処理の修復近傍**: 2 操作を消して再生し、見えている紙を1回動かして修復できるか試す。挿入位置の候補を最大 192 に広げる。操作数に加え、次注文に残す状態の推定費用に重みを掛け、目先の節約による次注文の悪化を抑える。大きな後処理は総経過時間・累積処理時間で打ち切る。
- **設計の評価**: 2商品共有の汎用層距離を双方の目標から見積もる。汎用窓数を36から38に変更し、窓割当の探索時間を0.40秒まで、その後のペア評価の hill-climb を0.70秒までとする。
- 補助紙候補を列上端から6枚（深さ0..5）までに広げ、重い後処理を1.73秒以降で止め、軽量計画への切替を1.85秒以降にした。

`main.cpp` は単一ファイルの C++23 ソースで、定数乱数seed、対話形式、`flush`、`CLOCK_SCALE` に対応。既存実装と同じ AVX2/FMA/BMI 対象関数が含まれる。標準出力は問題の設計と操作列だけに用いる。

## 重要: 出所・検証の境界

**このコミットの `main.cpp` は、前回ChatGPTが報告したLibrary保存版の完全な同一物ではない。** 以前のファイルへの直接アクセスがこの実行環境ではできず、リポジトリ内の `imp-post/main.cpp` に報告した変更を再構成している。したがって、前回報告の数値（10.643770 手/注文など）は**このコミットのソースを検証した結果ではない**。統合・提出前に公式テスタ・公式seed・`scripts/pahcer_run.py --compare` で必ず再評価すること。

変更の内容、前回報告の数値・条件、現状の未検証事項は [進捗報告](../../docs/chatgpt-layered-barcode-progress.md) に分けて記した。

## 主な値

`G=38`、`M=6`、`K=192`、`kFillerDepth=5`、`kEjectTrials=80`、`kEjectGaps=192`、`kEjectEvals=80`。時間: `kMapEnd=0.40`、`kGoptEnd=0.70`、`kAnnealEnd=1.305`、`kClimbEnd=1.36`、`kFastAfter=1.85`、大きな後処理は1.73以降停止。stderr は元の `imp-post` の `total_moves`、`post_saved`、`post_changed`、`eject_saved`、`req_sec` などを維持する。

## 評価

この再構成実装の公式seed評価は**未実施**。元の独自生成50ケース比較は別文書の「前回の報告」である。まず以下で確認する。

```sh
# main checkout で実行。完了後に runs/ と pahcer/ に残る
scripts/pahcer_run.py --compare solutions/imp-post solutions/chatgpt-layered-barcode-progress --seeds 0-50 --no-record -c "ChatGPT progress reconstruction sanity check"
# 安全性と速度が確認できた場合のみ 500 → 2000 へ拡張
```
