## 最終候補を絞る通常500件の測定

全て学習seed 0–499、24並列。正のp99差はこの比較では時間条件を満たさなかったことを表す。最終採否には事前固定した規則と2000件同時比較を用いる。

| 候補 | flex比 % ± SE | judge/old | p99−nofb ms | 設計差 ms | req差 ms | run |
|---|---:|---:|---:|---:|---:|---|
| deval-helpeq1 | -0.0217 ± 0.0033 | 1.08983 | -8.191 | -5.6513 ± 1.7811 | +9.8218 ± 1.4204 | `20261107-192415_deval-helpeq1` |
| deval-equalwide6 | -0.0311 ± 0.0035 | 1.10537 | +6.726 | +0.1737 ± 1.7897 | +23.4012 ± 1.3255 | `20261107-192415_deval-equalwide6` |
| deval-equalshift6 | -0.0079 ± 0.0206 | 1.10725 | +85.471 | -22.9176 ± 2.0355 | +48.3300 ± 1.4523 | `20261107-185353_deval-equalshift6` |
| deval-equalfund6 | -0.0057 ± 0.0206 | 1.10150 | +20.093 | -18.9852 ± 1.7975 | +38.1291 ± 1.7279 | `20261107-200401_deval-equalfund6` |
| deval-equalshift-fast | -0.0079 ± 0.0206 | 1.10935 | +36.497 | -18.3551 ± 1.8030 | +43.3666 ± 1.6603 | `20261107-201050_deval-equalshift-fast` |
| deval-equalfund-fast | -0.0057 ± 0.0206 | 1.09811 | +19.654 | -18.9611 ± 1.7565 | +31.0741 ± 1.6579 | `20261107-201050_deval-equalfund-fast` |
| deval-equalwide-fast | -0.0311 ± 0.0035 | 1.09440 | +5.282 | -4.4170 ± 1.7759 | +15.4673 ± 1.5456 | `20261107-201050_deval-equalwide-fast` |
| deval-helpeq-fast | -0.0217 ± 0.0033 | 1.08554 | -7.924 | -0.7177 ± 1.8496 | +2.3346 ± 1.4776 | `20261107-201050_deval-helpeq-fast` |
| deval-helper-fund | -0.0057 ± 0.0206 | 1.09501 | +29.226 | -19.4929 ± 1.7754 | +27.2220 ± 1.6314 | `20261107-202405_deval-helper-fund` |
| deval-helper-gap1 | -0.0023 ± 0.0206 | 1.08707 | +14.549 | -19.5005 ± 1.7813 | +17.6232 ± 1.6863 | `20261107-202405_deval-helper-gap1` |
| deval-helper-wide | -0.0311 ± 0.0035 | 1.09305 | +39.253 | -5.0288 ± 1.9865 | +12.4086 ± 1.6020 | `20261107-204516_deval-helper-wide` |
| deval-helper-one | -0.0217 ± 0.0033 | 1.08161 | +8.343 | -7.0709 ± 1.9394 | +0.8674 ± 1.4927 | `20261107-204516_deval-helper-one` |

## 出力一致の追加確認

`-march=native`の時間は採否に使わず、出力一致の検証だけに用いた。

| 比較 | compiler | 件数 | stdout一致 |
|---|---|---:|---:|
| `20261107-203310_deval-equalfund6` → `20261107-203310_deval-helper-fund` | GCC native | 200 | 200 |
| `20261107-203316_deval-equalfund6` → `20261107-203316_deval-helper-fund` | Clang native | 200 | 200 |
| `20261107-205620_deval-helpeq-fast` → `20261107-205620_deval-helper-one` | Clang | 200 | 200 |
| `20261107-205052_deval-equalwide-fast` → `20261107-205052_deval-helper-wide` | Clang | 200 | 200 |
| `20261107-204939_deval-helpeq-fast` → `20261107-204939_deval-helper-one` | GCC | 200 | 200 |
| `20261107-204839_deval-equalwide-fast` → `20261107-204839_deval-helper-wide` | GCC | 200 | 200 |
| `20261107-205745_deval-equalwide6` → `20261107-205745_deval-helper-wide` | Clang | 250 | 250 |
| `20261107-205534_deval-equalwide6` → `20261107-205534_deval-helper-wide` | GCC | 500 | 500 |
| `20261107-204736_deval-helper-wide` → `20261107-204736_deval-helper-hash2` | GCC | 250 | 250 |
