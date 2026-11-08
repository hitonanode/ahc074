from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-screen-replay/main.cpp').read_text()
a=s.index('    double donor(const Design::Unit& u,int slot=-1) const {');b=s.index('    // The filler value that the heads give',a)
s=s[:a]+'''    __attribute__((target("avx2"))) double donor(const Design::Unit& u,int slot=-1) const {
        AF_SCOPE(head_donor,64);
        double sum=0;
        const u64 dy=(u.b>=0?d.hb[u.a]^d.hb[u.b]:0)|extra_holes(slot);
        const u64 cover=low_bits(u.c+1)&~dy,bits=d.hb[u.a];
        const auto cv=_mm256_set1_epi64x(cover),bv=_mm256_set1_epi64x(bits),below=_mm256_set1_epi64x(low_bits(u.c));
        for(int t=0;t<P;t+=4) {
            const auto range=_mm256_and_si256(cv,_mm256_loadu_si256((const __m256i*)(target_holes.data()+t)));
            auto wrong=_mm256_and_si256(range,_mm256_xor_si256(bv,_mm256_loadu_si256((const __m256i*)(d.hb.data()+t))));
            // Set every bit below the highest mismatch. This is exactly low_bits(level),
            // including the zero case, and removes all bits if level reaches this column.
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,1));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,2));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,4));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,8));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,16));
            wrong=_mm256_or_si256(wrong,_mm256_srli_epi64(wrong,32));
            alignas(32) u64 covered[4];
            _mm256_store_si256((__m256i*)covered,_mm256_andnot_si256(wrong,_mm256_and_si256(range,below)));
            for(int lane=0;lane<4;++lane)if(target_column[t+lane]!=u.c)
                sum+=Design::covered_gain(covered[lane],[&](int j){return q[t+lane][j];});
        }
        return sum;
    }
'''+s[b:]
p=r/'solutions/dcomp-donor4';assert not p.exists();p.mkdir();(p/'main.cpp').write_text(s)
(p/'README.md').write_text('改良元: solutions/dcomp-screen-replay\n\nrematchのdonor評価で、4 targetの修復可能handle集合だけをAVX2で同時計算する。不一致の最上位bit以下をOR/shiftで塗り、従来のlevel cutoffと同じ集合を作る。確率多項式とsumは元のtarget順・演算のまま。探索、乱数、浮動小数点、候補数、ログ・実験スイッチを維持。\n')
