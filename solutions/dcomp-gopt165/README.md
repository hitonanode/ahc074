改良元: solutions/legal-tie-fast

dcomp-climb-cache の短縮時間を窓探索へ使う。map=450000、最後のclimb=165000反復。それ以外の反復数・候補数・注文処理は元のまま。

注文処理はlegal-tie-fastのまま。本文に記した変更以外の探索規則と既存のログ・実験スイッチを保つ。探索予算は固定回数で、時間不足の切替なし。標準runnerの24並列で比較する。
