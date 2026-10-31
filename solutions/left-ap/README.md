# left-ap

改良元: solutions/left-fast と solutions/mix-ap（合流）

left-fast（速くした焼きなまし）に、mix-ap の「焼きなましの中の穴埋めの proxy」をそのまま足した版。left-fast からは焼きなましの速さと、それまでの全部（audit2-blk までの注文処理）を、mix-ap からは焼きなましの費用に線形化した proxy V[x][l] を足す部分（ap_compute）だけを取った。

## 変更点

- 焼きなましの単位の移動・交換の費用に −0.5 × V[x][l] を足す。V は焼きなましの進捗 50% から 4 回計算し直して、その間は固定する。中身は mix-ap の README のとおり。
- left-fast で焼きなましの反復が増えたので、mix-ap（mix-pt の上での同じ変更）を試し直したもの（mix-pt の上での結果は trial_log.md の mix- の節）。

## パラメータと指標

- 環境変数 `AP_W`（既定 0.5）、`AP_START`（既定 0.5）、`AP_REFRESH`（既定 4）と、stderr の `ap_refreshes`・`ap_sec` は mix-ap と同じ。
