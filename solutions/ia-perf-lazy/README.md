改良元: solutions/dcomp-combo-dual30

穴あけのDPで、結果に使われない被覆情報の構築と行走査だけを省く。候補・目的関数・乱数・反復数・受理順は変えない。

- `Perforation::total_profit` の変更前後の署名は、穴を変えた紙だけを調べる。同じ列の反対色headの模様は変わらない。
- 変更した紙を所有しない同列の商品では、その列のdonorを使えず、DP辺も変わらないので全サンプルを無変更とする。
- 変更紙自身の対象と、変更サンプルが0個の対象は、非owner差分計算の前に飛ばす。`refresh_cache` も変更サンプルが0個なら被覆情報を構築しない。
- 穴を追加するowner補正では、変更前の被覆情報は変更handleの列だけ必要なので、その1列だけ作る。穴を戻す場合は元どおり全列を作る。

dual30の元行番号: `refresh_cache` 9711–9733、`total_profit` 9759–9870（署名9771–9802、非owner差分9805–9823、owner変更前geometry9841–9846）。整数のgeometry・DPと、浮動小数点の計算順は維持する。`perf_cache_skips` は、不要と証明できた行を追加で数えるため値が変わり得る。

検証は同じコンパイラのdual30とstdout完全一致、候補ごとのV/完成設計一致を先に確認し、GCCとClangのjudge flagsでpaired finish時間を測る。
