from merge_exact import *
for name,base in [('deval-equalshift-fast','deval-equalshift6'),('deval-equalwide-fast','deval-equalwide6'),('deval-helpeq-fast','deval-helpeq1')]:
 s=read(base);s=delta(s,read('deval-trim6b'),read('deval-ejectsimd6'));s=delta(s,read('deval-trim6b'),read('deval-keypack6'));s=drop_dead_features(s)
 detail='''ejectの必要条件を4紙ずつ整数AVX2で検査し、cache keyを16byte入力・8lane圧縮で作る。通過候補の順、キーの全一致検査、浮動小数点の計算は保つ。呼出しのないfeature exportメソッド2つと古いコメントを削除して容量を確保した。品質に関わる変更は次の改良元と同じである。\n\n'''+(ROOT/'solutions'/base/'README.md').read_text().split('\n\n',1)[1]
 emit(name,base,s,detail)
