# deval-screenmatch12

改良元: solutions/deval-fast2（出力を保つ高速化を加えたdeval-vbranch-nofb）。

4分岐の焼きなましは元のまま。各分岐を3通りの固定saltで再割当て2回まで仕上げる。climb50kの結果を各分岐内で共有する。穴あけ前のVで上位2候補を残し、その候補を穴あけ8サンプル・最終再割当て1回まで完成させ、完成Vで選ぶ。

計12候補の前半を作り、仕上げの後半は有望な候補に使う。dv_previewsは一次候補数、dv_candidatesは完成候補数。窓・anneal・注文の予算は元のまま。時間不足による打切りはない。DesignStore、ログ、@paper/@ops、目次・段の目印を維持。
