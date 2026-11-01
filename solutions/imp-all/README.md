# imp-all

改良元: solutions/imp-relax

設計の焼きなましに、solutions/imp-colswap-rp（cmp-anneal に別 agent が足したもの）の 2 つの手を入れた。imp-colswap-rp の cmp-anneal からの差分（Design と Annealer の部分）をそのまま当てただけで、注文処理と時間配分は imp-relax のまま（焼きなましは 1.305 秒まで）。

- 列の入れ替え（Annealer::column_swap）: 距離 4 以下の 2 列を、中の紙とハンドルの窓ごと入れ替える（手の 2%）。各紙は自分のハンドルの窓を保つので、対の条件と列の費用は変わらず、穴の数だけが変わる（solutions/gpt6pro-08-01-colswap、gpt6pro-06-02-regroup の近傍）。
- 対の組み替え（Annealer::multi_move）: 対 (a, b) + 単独 c, d → 対 (c, d) + 単独 a, b（手の 10%。新しい対は 3 列のうち自分のハンドルで一致する列から選ぶ。solutions/gpt6pro-07-02-replace の pair replace）。

手の詳しい中身・パラメータ（マクロ HSWAP_RATE / COLSWAP_RATE / COLSWAP_DIST / REPLACE_RATE / REPLACE_REPAIR）・stderr の `colswap_*` / `replace_*` は solutions/imp-colswap と imp-colswap-rp の README を参照。
