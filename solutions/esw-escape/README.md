# 中立探索 + filler climb の重みの直し + 後処理する計画 4 本（esw-escape）

改良元: solutions/opsearch-fast（solutions/esw-fixiter に、PR 114 の「2→2 中立リライト + 再短縮」を発展させた速い探索を Astra が入れたもの。系譜は esw-fixiter → neutral-port → opsearch-heavy → opsearch-fast。注文処理の詳細はそれぞれの README）

## 改良元からの差分

- **設計: filler climb の受理の重み**。filler climb は「両方の取っ手で色を保つ同じ種類の 2 単位の列の入れ替え」を `cur − λ × proxy` が下がれば採る（proxy は列の先頭の紙の穴埋めの価値）。λ を 1.0 → 0.5 にした（`Design::kClimbProxyWeight`）。
  - 理由（solutions/dsel-probe の計測、trial_log 2026-11-05）: 設計の乱数だけを変えた設計どうしの実際の手数は `cur − 0.74 × proxy` でよく説明できるが、proxy を最適化で直接上げると当てはまりの誤差を拾う。climb の λ を振ると 0.5 前後が最良（1000 件 × 注文列 4 本で λ 1.0 比 −0.072 ± 0.012%、0.4 / 0.6 は 0.5 と差なし、0 は悪化）。時間は変わらない。
- **注文処理: 後処理する計画を 2 → 4 本**（`Solver::kPostCandidates`）。PR 115 の「後処理の候補を 4 系統へ」。設計固定 2000 件で 3 本 −0.032 ± 0.001%、4 本 −0.040 ± 0.001%（注文処理の時間 +12%）。
- 中立探索（1→1 の修復、新しい紙を使う中立候補の再短縮、最大 2 周）と、その環境変数・stderr の指標は改良元と同じ。`NEUTRAL=0` で中立探索を止める。

## 時間

- 設計は esw-fixiter と同じ回数（ジャッジ Clang で平均約 1.30 秒の見積り）。注文処理は esw-fixiter の約 1.5 倍（中立探索）× 約 1.1 倍（計画 4 本）。注文処理のペース配分（Pacer）は改良元のまま（遅れたら後処理を段階的に省く。LOCAL_BENCH では常に全部行う）。
