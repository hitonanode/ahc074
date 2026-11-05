改良元: solutions/argon-des-perf-gaincache

測定専用。色標本を512個に増やし、係数0.8で穿孔する。
owner側の条件付け、上限、差分キャッシュは基準と同じ。
現在の係数の下で標本誤差を減らした時の到達点を見る。真の最適設計を返すオラクルではない。
時間超過の可能性が高いため、通常評価でも --no-record を使う。

d2_cost_delta/profit_deltaは穴費用と未補正利益の変化（手/注文）。
d2_predictionは受理係数とowner補正を含む予測変化。
追加の環境変数はない。全既存ログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、
LOCAL_BENCH、DesignStore、段の目印と目次を保持する。
