改良元: solutions/argon-des-design-packed

基準と同じheadの穿孔の後、各列・色の2番目の紙も候補にする。
2番目の露出確率を.0625、先頭を残りとする紙IDの32層化標本を使う。
色は基準の32層化標本。所有目標の色条件付け、上限と差分キャッシュを保持する。
追加段も係数0.7。追加段に入る際に、現在の穴数から色確率と標本を一度作り直す。
固定headの穴は追加段では変更しない。未来の注文は使わない。

d2_trials/viable/acceptedは追加段の候補数・事前評価通過数・受理数。
d2_cost_delta/profit_delta/corrected_deltaは穴コスト・未補正利益・補正利益の変化（手/注文）。
d2_secは追加段の時間。追加の環境変数はない。
既存のログ・@paper/@ops・プロファイラ・予算スイッチ、CLOCK_SCALE、LOCAL_BENCH、
DesignStore、段の目印と目次を保持する。
