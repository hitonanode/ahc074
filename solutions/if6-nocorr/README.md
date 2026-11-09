# if6-nocorr: 列費用の「対が全部同じ色なら np−1 を足す」補正を外す

改良元: solutions/d30a-reset6

- `Design::least_depths2`（と Annealer の SIMD 版 `colcost_pair`）で、列の対がすべて同じハンドル色のときに足していた補正 np−1（他の色の単独が 2 番目に入り、対が 1 段沈むという仮定）を、定数 kPairColorCorr（既定 0）倍にする。
- 理由: この補正は「列の上 2 枚に両色を置く」古い規則を列費用に埋め込んだもので、今の注文処理は列内の初期順を需要で決め（improve_initial_columns）、reset6 の焼きなましは取っ手の頭が多数色へ戻る前提で少数色の穴を減らす。少数色の需要が小さい列で他色の紙を 2 番目に置く必要はなく、補正は偏った列を不当に罰する。
- LOCAL_BENCH では環境変数 IF6_CORR=1 で元に戻る。ほかは d30a-reset6 のまま。
