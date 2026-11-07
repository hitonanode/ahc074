改良元: `solutions/deval-helper-wide`。

後処理のfinal-state memoのhashを2本の独立な整数積へ分け、最後に混ぜる。従来と同じ全successor配列の一致検査を保持するため、hash衝突は誤ったcache hitにはならない。memoの置換位置だけが変わる。固定予算・探索順・浮動小数点計算・設計・操作ラベルとログは保つ。時刻による切替えはない。hashの変更が操作列と速度へどう影響するかを測る出力同一実験。
