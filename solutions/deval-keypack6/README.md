改良元: `solutions/deval-trim6b`。

adaptive_next_costのcache keyを作る走査を、16 byteずつの整数SIMDと8 byte圧縮tableに変える。非column紙・top_d・fillersを除いた紙番号は元の順に保存し、hash・完全一致検査・浮動小数点計算は変えない。roleが通常の番号配置でない設計には元の走査を使う。これは設計形式による分岐であり時間で探索を変えない。ログ・統計・profiler・実験switchを保つ。
