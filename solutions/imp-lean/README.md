# imp-lean

改良元: solutions/imp-all

imp-all のリファクタリング。3862 → 3467 行。

出力を変えない整理（回数を固定して seed 0〜15 で imp-all と出力が一致）:

- 冒頭の改良の履歴のコメントを消した（履歴は各解法の README と trial_log にある）
- 焼きなましの手の割合のマクロ（HSWAP_RATE など）を定数にし、使わない分岐（REPLACE_REPAIR = 0）を消した
- 実験用の `-DANNEAL_CHECK`、`-DFORCE_FAST_MODE`、`-DFORCE_EMERGENCY_DESIGN` を消した
- 後処理の使っていない近傍（2 手削除と eject、POST_PAIRS = 0 で無効だったもの）と、その stderr を消した
- 使われていない Design::move_col、relist と列ごとの単位の表を消した

注文ごとの計画の候補のうち、外しても最良の費用がほとんど変わらないもの（seed 0〜3 で 1 ケースあたり 0〜4）を除いた（solutions/lean-a）:

- keep（持ち上げた紙が要求の紙なら上に置いたまま）、fret_mode 2（古い穴埋め紙を一番上の罰なしで全部戻す）と 3（害がなくても残さない。fret_mode 4 は「害がなければ残す」を常に行う）、fret_ret 0（戻すときに一番上の罰なし）
- merge_double_moves（同じ紙を 2 回動かす手の合成。後処理が同じ手を見つける）

汎用層の距離（solutions/lean-g）: 設計で使う汎用層の手数の見積り（Comparator::mean_moves、gcost）の距離を、「どの紙も動かせる」ときの M − 最長共通部分列から、最下段の紙を動かさないときの正確な最少手数（720 通りの順序の BFS）に変えた。注文処理の並べ替え（Comparator::plan）は元からこの制約の下での最短なので、モデルが実際の手数に揃う。この表（順序、1 手で移る先 next、距離 dist）を補助紙（Interleave）と共有し、補助紙の側の順序・BFS・最初の手の表を消した（汎用紙を目標の順序へ動かす手は Comparator::path が距離から復元する。回数固定で seed 0〜15 の出力が lean-g と同一）。

残したもの（外すと悪化、500 件の切り分け）: 穴埋めの山登り（Design::filler_climb）、補助紙 2 枚の組、穴埋め紙の 2 枚重ね、窓の割り当ての gobj の山登り。安全網（設計のやり直し、緊急設計、軽量処理）と実験用の回数固定・模擬（SIM_HARNESS）も残した。
