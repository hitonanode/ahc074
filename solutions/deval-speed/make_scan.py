from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
idx=s.index('WindowStats assign_windows(')
s=s[:idx]+'''// Exact exclusive scan of radix counts, eight bins per carry dependency.
__attribute__((target("avx2"))) void radix_scan(int* values,int begin,int end) {
    int carry=0;
    for(;begin+8<=end;begin+=8) {
        const __m256i input=_mm256_loadu_si256(reinterpret_cast<const __m256i*>(values+begin));
        __m256i sum=input;
        sum=_mm256_add_epi32(sum,_mm256_slli_si256(sum,4));
        sum=_mm256_add_epi32(sum,_mm256_slli_si256(sum,8));
        const int low=_mm256_extract_epi32(sum,3);
        sum=_mm256_add_epi32(sum,_mm256_setr_epi32(carry,carry,carry,carry,carry+low,carry+low,carry+low,carry+low));
        carry=_mm256_extract_epi32(sum,7);
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(values+begin),_mm256_sub_epi32(sum,input));
    }
    for(;begin<end;++begin){const int n=values[begin];values[begin]=carry;carry+=n;}
}
'''+s[idx:]
lo=s.index('        for (int i = 0, l = 0; i < 256; ++i) {',s.index('auto matching_cost ='))
hi=s.index('        for (int i = 0; i < size; i++) tmp[',lo)
s=s[:lo]+'''        radix_scan(low.data(),0,256);
        radix_scan(high.data(),min_high,max_high+1);
'''+s[hi:]
d=ROOT/'solutions/deval-radixscan';d.mkdir(exist_ok=True)
(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-radixscan

改良元: solutions/deval-vbranch-o3。

窓割当ての基数ソートでヒストグラムの累積和を8整数ずつAVX2で計算する。整数の正確な累積和であり、安定ソートの順序と結果は同じ。探索予算、浮動小数点の式、時間ガードは変更しない。
''')
print(len(s.encode()))
