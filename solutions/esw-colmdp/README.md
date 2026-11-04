# 速い中立探索（fast2）+ 列の部分列 MDP + filler climb の重みの直し（esw-colmdp）

改良元: solutions/opsearch-fast2（Astra。esw-fixiter → neutral-port → opsearch-heavy → opsearch-fast → opsearch-fast2 の系譜で、PR 114 の中立リライトを速くした注文処理）に、solutions/colmdp（PR 115 の列の部分列 MDP を esw-fixiter に移植したもの）の差分と、solutions/esw-escape の設計の変更を足した。

## 改良元からの差分

- **列の部分列 MDP（solutions/colmdp の差分をそのまま当てた）**: 列ごとに、紙の種類（担当する目標の数 × 取っ手の色）の並びの長期の価値を小さな平均費用 MDP で前計算し、掘り・戻しの差し込み位置（adaptive_insert）では 1 手先の模型と半々に混ぜ、状態の評価（adaptive_next_cost）には半分を足す。詳細と計測は solutions/colmdp/README.md・REPORT.md（esw-fixiter 比、設計固定 2000 件 −0.100 ± 0.003%、注文処理 +5.7%）。`COLMDP=0` で止まる。
- **設計: filler climb の受理の重み λ を 1.0 → 0.5**（`Design::kClimbProxyWeight`。理由は solutions/esw-escape/README.md と trial_log 2026-11-05）。
- 注文処理の探索（fast2 の `F2_MODE=1` が既定）と、その環境変数・stderr の指標は改良元と同じ。`NEUTRAL=0` で中立探索を止める。

## 時間

- 設計は esw-fixiter と同じ回数（前計算の MDP が約 10 ms 増える）。注文処理は esw-fixiter の約 1.5 倍（fast2）× 約 1.06 倍（MDP）。
- **時間不足用の fallback はない**（fallback を外す PR で、esw-pace 以来の注文処理のペース配分（Pacer）と軽い計画を取り除いた。どの注文も常に全部の探索を行う。提出の前に戻すなら、その PR の差分を逆に当てる）。
