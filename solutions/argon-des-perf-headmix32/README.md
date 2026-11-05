改良元: solutions/argon-req-filterblocks-v2

穿孔のフィラーモデルに列・色の第2候補も含め、その露出率を.0625とする。
色と紙IDにそれぞれ32層化標本を使う。所有目標の色条件付けと差分キャッシュは保持。
head・第2候補の全ての穴候補を一緒に並べ、係数0.7で一巡する。
通常のheadだけの穿孔を先に行う追加段はなく、区間DPの初期構築も一度にする。
前段の割当・ペア・列と注文処理は基準と同じ。未来の注文は使わない。

d2_trials/viable/acceptedは非head候補の試行・事前評価通過・受理数。
d2_cost_delta/profit_delta/corrected_deltaは非head候補だけの予測変化（手/注文）。
d2_secは混合モデルの構築と一巡の時間。perforation_*は両方を含む全体値。
追加の環境変数はない。既存ログ・@paper/@ops・プロファイラ・予算スイッチ、
CLOCK_SCALE、LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
