改良元: solutions/argon-req-filldp-positive

D2の診断から得た穿孔差分の補正。head穿孔と非head第2候補の追加穿孔を補正する（露出率0.125）。
変更紙自身の目標は、追加する穴の色の標本数が8または16しかない。
標本のその色を反転した場合の差分も計算し、列頭色の既存確率で重み付けする。
その他の窓と候補の順序、8標本、一次判定は維持する。
受理には補正した差分を使い、DPキャッシュは元の標本の値を維持する。

perf_owner_raw / perf_owner_conditionedは受理した変更の自目標の利益（補正前後、手/注文）。
perf_donor_gainは他目標の利益。既存のperforation指標も維持する。
ARGON_D2_RATE / WIDTH と d2_* はargon-des-perforationと同じ。
ログ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持する。
共通報告はsolutions/argon-des-perforation/REPORT.md。

PR #137の新基準へ同じ穿孔変更を移植。注文処理の基準変更を保持する。

条件付けの旧状態側では、穴を開ける前の窓は商品紙で覆われている。
その窓の列頭色を変えても、当該列から取るフィラーの価格しか変わらない。
全列DPの再計算を避け、既存のavoid/forward/backwardと1列の再評価で同じ最適値を求める。
