改良元: solutions/argon-des-perf-nonhead32wide-v2

非head露出1/8の追加段で、所有目標の利益係数だけを0.7から0.5へ下げる。
donor側は0.7のまま。headの最初の穿孔は0.7のまま。
既存の所有目標の上限は保守的な上限として有効。
d2_corrected_deltaは受理用に所有目標利益を0.5/0.7倍した値、
perf_owner_conditionedは従来どおり倍率を掛ける前の利益。

色・紙IDは32層化標本。未来の注文は使わない。
スイッチと指標は改良元と同じ。既存ログ、@paper/@ops、プロファイラ、予算スイッチ、
CLOCK_SCALE、LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
