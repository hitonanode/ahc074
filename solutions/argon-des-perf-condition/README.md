改良元: solutions/esw-slim

D2の診断から得た穿孔差分の補正。元のhead穿孔だけを補正する。
変更紙自身の目標は、追加する穴の色の標本数が8または16しかない。
標本のその色を反転した場合の差分も計算し、列頭色の既存確率で重み付けする。
その他の窓と候補の順序、8標本、一次判定は維持する。
受理には補正した差分を使い、DPキャッシュは元の標本の値を維持する。

perf_owner_raw / perf_owner_conditionedは受理した変更の自目標の利益（補正前後、手/注文）。
perf_donor_gainは他目標の利益。既存のperforation指標も維持する。
追加の環境変数はない。
ログ・プロファイラ・CLOCK_SCALE・LOCAL_BENCH・DesignStore・段の目印と目次を保持する。
共通報告はsolutions/argon-des-perforation/REPORT.md。
