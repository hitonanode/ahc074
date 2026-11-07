from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
s=(ROOT/'solutions/deval-vbranch-o3/main.cpp').read_text()
a=s.index('inline CoverResult expectation(')
prefix=s.rfind('__attribute__((target("popcnt")))',0,a)
s=s[:prefix]+s[prefix:].replace('__attribute__((target("popcnt")))','__attribute__((target("avx2,popcnt")))',1)
old='''            for(int c=0;c<s.H;++c)
                colors|=U64((draws[sample][c]^shifts[t][c])<threshold[c])<<c;'''
new='''            // Every draw/shift has 30 bits and thresholds lie in [0,2^30],
            // so signed AVX2 comparison is identical to the scalar unsigned one.
            // Zero threshold padding also makes all lanes beyond H false.
            for(int c=0;c<s.H;c+=8) {
                const auto draw=_mm256_loadu_si256(reinterpret_cast<const __m256i*>(draws[sample].data()+c));
                const auto shift=_mm256_loadu_si256(reinterpret_cast<const __m256i*>(shifts[t].data()+c));
                const auto th=_mm256_loadu_si256(reinterpret_cast<const __m256i*>(threshold.data()+c));
                const auto bits=_mm256_cmpgt_epi32(th,_mm256_xor_si256(draw,shift));
                colors|=U64(unsigned(_mm256_movemask_ps(_mm256_castsi256_ps(bits))))<<c;
            }'''
assert old in s;s=s.replace(old,new,1)
s=s.replace('std::array<std::uint32_t,MaxH>', 'std::array<std::uint32_t,MaxH+1>')
d=ROOT/'solutions/deval-vcolors';d.mkdir(exist_ok=True);(d/'main.cpp').write_text(s)
(d/'README.md').write_text('''# deval-vcolors

改良元: solutions/deval-vbranch-o3。

Vの固定積分点から列先頭の色を作る処理を8列ずつのAVX2整数演算へ置き換える。入力は30ビットの非負整数、確率しきい値は0〜2^30なので符号付き比較でも結果は同じ。Hを超えるしきい値は0で、余分なビットは立たない。積分点・DP・浮動小数点の足し算の順・候補選択・探索回数・時間ガードは同じ。
''')
print(len(s.encode()))
