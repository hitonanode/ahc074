from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/dcomp-stack-b/main.cpp').read_text()
a=s.index('    __attribute__((target("ssse3,sse4.1,popcnt"))) double adaptive_next_cost(');b=s.index('    // Lexicographic permutation rank',a);t=s[a:b]
t=t.replace('target("ssse3,sse4.1,popcnt")','target("avx2,popcnt")')
x='''        for (int c = 0; c < H; c++)
            for (int color = 0; color < 2; color++) {
                int fixes = available[2 * c + color] ? 0 : first[2 * c + color];
                if (fixes < 0) fixes = rank[c];
                cost += (adaptive_holes[c][color] - kCoverStrength * covered[c][color]) * fixes;
            }'''
y='''        // All hole rates and stay covers are integer multiples of 1/P. With
        // kCoverStrength=.25 and integer depths, each term is exact on a 1/1024
        // grid. Computing four terms separately cannot alter FMA rounding; the
        // additions to the general running cost retain their original order.
        int hc=0;
        for(;hc+2<=H;hc+=2) {
            auto fixes=_mm_loadu_si128((const __m128i*)(first.data()+2*hc));
            const auto ranks=_mm_set_epi32(rank[hc+1],rank[hc+1],rank[hc],rank[hc]);
            fixes=_mm_blendv_epi8(fixes,ranks,_mm_cmpgt_epi32(_mm_setzero_si128(),fixes));
            uint32_t av;std::memcpy(&av,available.data()+2*hc,4);
            const auto keep=_mm_cmpeq_epi32(_mm_cvtepu8_epi32(_mm_cvtsi32_si128(av)),_mm_setzero_si128());
            fixes=_mm_and_si128(fixes,keep);
            const auto rates=_mm256_sub_pd(_mm256_loadu_pd(adaptive_holes[hc].data()),
                _mm256_mul_pd(_mm256_set1_pd(kCoverStrength),_mm256_loadu_pd(covered[hc].data())));
            alignas(32) double terms[4];
            _mm256_store_pd(terms,_mm256_mul_pd(rates,_mm256_cvtepi32_pd(fixes)));
            for(int lane=0;lane<4;++lane)cost+=terms[lane];
        }
        for(;hc<H;++hc)for(int color=0;color<2;++color) {
            int fixes=available[2*hc+color]?0:first[2*hc+color];
            if(fixes<0)fixes=rank[hc];
            cost+=(adaptive_holes[hc][color]-kCoverStrength*covered[hc][color])*fixes;
        }'''
assert t.count(x)==1;t=t.replace(x,y);s=s[:a]+t+s[b:]
for check in [False,True]:
 p=r/'solutions'/('dcomp-hole4'+('-check' if check else ''));assert not p.exists();p.mkdir();(p/'main.cpp').write_text(('#define NEXT_PREFIX_CHECK\n' if check else '')+s)
 (p/'README.md').write_text('改良元: solutions/dcomp-stack-b\n\nnext_costの穴費用の4色分をAVX2で計算し、元の順にcostへ加える。穴需要率と残留カバー率はいずれも整数/256、係数は.25、深さは整数なので各項が整数/1024として正確に表せる。積や差の丸めがなく、FMAの有無に左右されない。一般の途中和への加算順は変更しない。検証版は旧next_costで全missを再計算しdouble bitを照合。\n\n予算・列挙順・ログ・DesignStore・実験スイッチはそのまま。時間fallbackなし。\n')
