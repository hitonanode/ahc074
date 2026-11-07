from pathlib import Path
P=Path(__file__).resolve().parent;R=P.parents[1]
s=(R/'solutions/deval-target-delta/main.cpp').read_text()
old='''            _Pragma("GCC unroll 5") for(int r=0;r<NR;++r)common[r]=_mm256_setzero_ps();
            add_bits(common,pair_holes(ox),-1.f);
            add_bits(common,pair_holes(nx),1.f);
            add_bits(common,pair_holes(oy),-1.f);
            add_bits(common,pair_holes(ny),1.f);'''
new='''            const u64 ax=pair_holes(nx),ay=pair_holes(ny),bx=pair_holes(ox),by=pair_holes(oy);
            const u64 plus1=ax^ay,minus1=bx^by,plus2=ax&ay,minus2=bx&by;
            _Pragma("GCC unroll 5") for(int r=0;r<NR;++r) {
                const int shift=8*r;
                const auto low=_mm256_sub_ps(_mm256_load_ps(bit_lanes((plus1>>shift)&255)),
                    _mm256_load_ps(bit_lanes((minus1>>shift)&255)));
                const auto high=_mm256_sub_ps(_mm256_load_ps(bit_lanes((plus2>>shift)&255)),
                    _mm256_load_ps(bit_lanes((minus2>>shift)&255)));
                common[r]=_mm256_fmadd_ps(high,_mm256_set1_ps(2.f),low);
            }'''
assert old in s;s=s.replace(old,new,1)
p=R/'solutions/deval-target-plane';p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: `solutions/deval-target-delta`。\n\nペア差分の穴需要をbitごとの1桁・2桁にまとめ、SIMD加算4回の依存列を独立な2つの差と1回のFMAへ替える。全て小整数であり、穴数と費用の丸め、乱数・探索予算は同じ。\n')
print(p.name,len(s.encode()))
