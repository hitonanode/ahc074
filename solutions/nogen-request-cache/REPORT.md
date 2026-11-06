# 注文処理の統合と通常比較での時間の再確認

主な変更は、不要な距離表の省略、距離表の番号置換、背景候補順と正解状態の前計算、実際の主紙だけに需要を与える列模型、背景の1段先読み、同距離の単独補助紙、通常候補と中立書換の予算追加。

途中の統合は [nogen-request-stack10](../nogen-request-stack10/REPORT.md)、実需要の修正は [nogen-true-demand](../nogen-true-demand/REPORT.md)、後処理予算は [nogen-post-four](../nogen-post-four/REPORT.md)、完全一致高速化は [nogen-canon-fast](../nogen-canon-fast/REPORT.md) を参照。

`20261106-140833_` の通常500件比較では、SOTA judge 1.570458秒に対しrequest-cache 1.750835秒、request-five（列9.5M・通常5候補）1.768330秒。両方時間超過のため延長・採用しない。平均スコアはそれぞれ10372.734と10376.258。SOTA比 +0.562346 ± 0.050485%、158/1/341、および +0.596412 ± 0.052421%、146/0/354。five対cache +0.034066 ± 0.047265%は未確定。個別の設計固定比較で速くなった手法を統合しても、通常比較で同じ短縮になるとは限らなかった。

最後は比較窓を考慮した背景補助紙の再利用率補正を採用し、個別正規化に戻して時間条件を測り直す。結果はnogen-payload-post4系のREPORTに記載する。

## 構造模型と棄却理由

- [pair-rollout64-model](../nogen-pair-rollout64-model/REPORT.md): 保存スタック64個で実際の取り出し計画を費用行列にした。静的予測+0.0824手に対し独立通常注文では−0.0851±0.0175手の悪化。ペア変更は全商品の補助紙としての用途と定常状態を変えるため、割当先の商品2個だけの費用では足りない。
- [window-rollout-model](../nogen-window-rollout-model/REPORT.md): G35/37/38を独立注文列で比較。G37は速度を大きく改善したがスコア差は未確定。通常2000件での検証は [g37-full-fast](../nogen-g37-full-fast/REPORT.md)。
- [window-swap-model](../nogen-window-swap-model/REPORT.md): 比較窓と取っ手窓の同時交換。所有者が対応可能な2074.5候補に対し全商品で可能なのは0.34375候補／ケース、改善受理0。ペア固定の完成設計を少し動かす近傍はほぼ閉じている。
- [helper-prefill-model](../nogen-helper-prefill-model/REPORT.md): 背景補助紙を条件に区間DPを先行実行。独立通常注文で+0.000687±0.000926手／注文、時間は増加。大きな実装へ進めない。
- [retain-shared](../nogen-retain-shared/REPORT.md): 旧補助紙を残す候補は強化後の基準では有意差なし。単独候補の事後改善だけを全体の利得と見なさない。
- [demand-rollout-model](../nogen-demand-rollout-model/REPORT.md): 過去の独立訓練列で選ばれた補助紙頻度を列需要へ加えると、別の検証列で悪化。選択された頻度は外生的な需要ではない。

## 残った操作差

G36-deepとSOTAの2000件では、注文あたりfix +0.07717、help +0.07473、fret +0.05287、hdig +0.03402、lift +0.03437。dig −0.12935、gen −0.04675、repair −0.04243が一部を相殺する。perf-reuseからはfixを0.07934減らしたが、help +0.02868、fret +0.03529が戻り費用として増えた。再利用率補正はこのずれを狙った。

次の構造変更は窓・ペアを同時に動かし、全商品の補助紙価値と独立注文の定常状態を含めて判断する。背景補助紙については前後の順番を変えるだけの小変更でなく、補助紙集合と挿入位置を背景状態と一体で選ぶ模型が必要。
