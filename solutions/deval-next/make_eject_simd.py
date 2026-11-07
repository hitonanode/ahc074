from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/deval-eject-right/main.cpp').read_text()
s=s.replace('''    void eject_repairs(const State& initial''','''    __attribute__((target("avx2"))) void eject_repairs(const State& initial''',1)
s=s.replace('''        std::array<int, K> candidates;
        int candidate_count = 0;''','''        std::array<int, K+4> candidates{};
        int candidate_count = 0;''',1)
s=s.replace('''        std::array<u64,K> candidate_wrong, candidate_right;''','''        std::array<u64,K+4> candidate_wrong{}, candidate_right{};''',1)
s=s.replace('''        std::array<u64, K> owned;
        std::array<int, 64> first, second, column_first, column_second;''','''        std::array<u64, K> owned{};
        std::array<int, 64> first, second, column_first, column_second;''',1)
needle='''                for (int ci = 0; ci < candidate_count; ci++) {
                    const int k = candidates[ci];'''
replacement='''                // Necessary color/opacity test, four candidates at once. Preserve
                // candidate order and run the same scalar repair logic for survivors.
                std::array<int,K+4> survivors;
                int survivor_count=0;
                const __m256i base_bad=_mm256_set1_epi64x((long long)(shown^A[u]));
                const __m256i change=_mm256_set1_epi64x((long long)(shown^second_black));
                const __m256i zero=_mm256_setzero_si256();
                for(int ci=0;ci<candidate_count;ci+=4){
                    const __m128i ids=_mm_loadu_si128((const __m128i*)(candidates.data()+ci));
                    const __m128i stamps=_mm_i32gather_epi32(owner_stamp.data(),ids,4);
                    const __m256i mask=_mm256_cvtepi32_epi64(_mm_cmpeq_epi32(stamps,_mm_set1_epi32(trial_stamp)));
                    const __m256i own=_mm256_and_si256(mask,_mm256_i32gather_epi64((const long long*)owned.data(),ids,8));
                    const __m256i bad=_mm256_xor_si256(base_bad,_mm256_and_si256(change,own));
                    const __m256i right=_mm256_loadu_si256((const __m256i*)(candidate_right.data()+ci));
                    const __m256i good=_mm256_andnot_si256(_mm256_cmpeq_epi64(bad,zero),_mm256_cmpeq_epi64(_mm256_andnot_si256(right,bad),zero));
                    unsigned bits=unsigned(_mm256_movemask_pd(_mm256_castsi256_pd(good)));
                    for(;bits;bits&=bits-1){int x=ci+__builtin_ctz(bits);if(x<candidate_count)survivors[survivor_count++]=x;}
                }
                for(int si=0;si<survivor_count;++si) {
                    const int ci=survivors[si];
                    const int k = candidates[ci];'''
assert needle in s;s=s.replace(needle,replacement,1)
p=r/'solutions/deval-eject-simd';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`（deval-eject-rightの固定色マスクも使用）。\n\n2削除1修復の候補について、色と不透明窓の必要条件をAVX2で4枚ずつ検査する。通過した紙を元の順序で元の修復手順に渡す。整数計算のみで、探索予算と浮動小数点の演算順は変えない。時間による打切りはない。\n');print(len(s.encode()))
