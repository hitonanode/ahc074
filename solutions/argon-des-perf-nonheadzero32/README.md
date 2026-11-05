改良元: solutions/argon-des-perf-nonhead32wide-v2

非headの露出確率を0にする対照。第2候補の穴は探索するが、
区間DPにその紙をフィラーとして出さない。他のheadがその紙の所有目標を修復する
モデル利益だけで穴が選ばれるかを確かめる。headの最初の穿孔は基準どおり。

色・紙IDは32層化標本。未来の注文は使わない。
スイッチと指標は改良元と同じ。既存ログ、@paper/@ops、プロファイラ、予算スイッチ、
CLOCK_SCALE、LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
