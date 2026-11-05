改良元: solutions/argon-des-design-packed

32個の層化色標本を用いる穿孔の受理係数だけを0.7から0.65に変える。
列の穴コスト増分から、係数×条件付け補正済みフィラー利益を引いた値で受理する。
窓割当、ペア・列・ハンドル、フィラー交換、Hungarian、注文処理は基準と同じ。

新しいスイッチと指標はない。perforation_holes、perf_owner_raw、
perf_owner_conditioned、perf_donor、および既存の時刻・プロファイラで比較する。
既存のログ、@paper/@ops、CLOCK_SCALE、LOCAL_BENCH、DesignStore、段の目印と目次を保持。
