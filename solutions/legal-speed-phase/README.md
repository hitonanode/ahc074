# legal-speed-phase（legal-tie-fast の注文処理の段ごとの時間だけを測る版）

改良元: `solutions/legal-speed-prof`。出力は legal-tie-fast と同じ（時間を測るだけ）。提出用ではない。

## 改良元からの差分

- 関数ごとの計測（CF_SCOPE）を止め、process() の段ごとの時間（`phase_<段>_ms`、`phase_<段>_calls`、`phase_sum_ms`）だけを測る。計測の回数が注文あたり約 15 回になり、計測で遅くなる分がほぼなくなる（legal-speed-prof は関数ごとの計測で 1 ケースあたり約 41 ms 遅い）。
