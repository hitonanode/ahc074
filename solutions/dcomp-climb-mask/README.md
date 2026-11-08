改良元: solutions/legal-tie-fast

dcomp-climb-cache に加え、確率計算の寄与を (target ID, covered mask) の完全キーで記憶する。列移動後も同じ範囲を覆う場合に再利用する。q の丸めがtargetごとに異なりうるため、色だけの共有はしない。16384スロット、climbごとに初期化。

注文処理はlegal-tie-fastのまま。本文に記した変更以外の探索規則と既存のログ・実験スイッチを保つ。探索予算は固定回数で、時間不足の切替なし。標準runnerの24並列で比較する。
