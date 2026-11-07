from pathlib import Path
r=Path(__file__).resolve().parents[2];s=(r/'solutions/deval-seven-wide/main.cpp').read_text()
needle='''    std::vector<int> u, v;
    void push'''
new='''    std::vector<int> u, v;
    // Trial geometry is retained until acceptance, so incompatible blocks can
    // defer their otherwise-unused relation update without changing any cost.
    std::array<u64,512> trial_af,trial_ar,trial_bf,trial_br;
    uint32_t trial_erase=0,trial_fa=0,trial_fb=0;
    bool trial_two=false,dirs_incomplete=false;
    void push'''
assert needle in s;s=s.replace(needle,new,1)
needle='''    u64 af[512], ar[512], bf[512], br[512];'''
assert needle in s;s=s.replace(needle,'''    auto* af=P.trial_af.data();auto* ar=P.trial_ar.data();
    auto* bf=P.trial_bf.data();auto* br=P.trial_br.data();
    P.trial_erase=uint32_t(erase);P.trial_fa=uint32_t(fa);P.trial_fb=uint32_t(fb);
    P.trial_two=TwoEdges;P.dirs_incomplete=false;''',1)
needle='''            __m256i r = _mm256_and_si256(dir, vkeep);
            const __m256i ar ='''
new='''            __m256i r = _mm256_and_si256(dir, vkeep);
            const __m256i possible=_mm256_cmpeq_epi32(_mm256_and_si256(r,_mm256_srli_epi32(r,16)),zero);
            if(_mm256_testz_si256(possible,possible)) {
                // Opposite arcs outside the changed edges cannot be repaired.
                _mm256_storeu_si256((__m256i*)(ndir+p),dir);
                _mm256_storeu_si256((__m256i*)(nrel+p),zero);
                a_fwd>>=8;a_rev>>=8;
                if constexpr(TwoEdges){b_fwd>>=8;b_rev>>=8;}
                P.dirs_incomplete=true;
                continue;
            }
            const __m256i ar ='''
assert needle in s;s=s.replace(needle,new,1)
marker='''// AS_PROFILE adds operator yield and cycle counts without changing proposals.'''
helper='''// Materialize all relation lanes only for an accepted trial. The cheap full
// pass uses the exact bitsets that evaluate_move collected; no closures or costs.
AVX2_TARGET void complete_pair_dirs(const WindowPairs& p,uint32_t* out) {
    alignas(32) static const auto lanes=[] {
        std::array<std::array<uint32_t,8>,256> a{};
        for(int v=0;v<256;++v)for(int j=0;j<8;++j)a[v][j]=(v>>j)&1;
        return a;
    }();
    const __m256i keep=_mm256_set1_epi32(int(~p.trial_erase));
    const __m128i sa=_mm_cvtsi32_si128(__builtin_ctz(p.trial_fa));
    const __m128i sb=_mm_cvtsi32_si128(__builtin_ctz(p.trial_fb));
    for(int w=0;w<p.words;++w) {
        u64 af=p.trial_af[w],ar=p.trial_ar[w],bf=0,br=0;
        if(p.trial_two){bf=p.trial_bf[w];br=p.trial_br[w];}
        for(int i=w*64;i<std::min(p.n8,(w+1)*64);i+=8) {
            __m256i v=_mm256_and_si256(_mm256_loadu_si256((const __m256i*)(p.dir.data()+i)),keep);
            const __m256i a=_mm256_or_si256(_mm256_load_si256((const __m256i*)lanes[af&255].data()),_mm256_slli_epi32(_mm256_load_si256((const __m256i*)lanes[ar&255].data()),16));
            v=_mm256_or_si256(v,_mm256_sll_epi32(a,sa));af>>=8;ar>>=8;
            if(p.trial_two) {
                const __m256i b=_mm256_or_si256(_mm256_load_si256((const __m256i*)lanes[bf&255].data()),_mm256_slli_epi32(_mm256_load_si256((const __m256i*)lanes[br&255].data()),16));
                v=_mm256_or_si256(v,_mm256_sll_epi32(b,sb));bf>>=8;br>>=8;
            }
            _mm256_storeu_si256((__m256i*)(out+i),v);
        }
    }
}

'''
assert marker in s;s=s.replace(marker,helper+marker,1)
needle='''        pairs.dir.swap(ndir);
        pairs.rel.swap(nrel);'''
assert needle in s;s=s.replace(needle,'''        if(pairs.dirs_incomplete)complete_pair_dirs(pairs,ndir.data());
'''+needle,1)
p=r/'solutions/deval-map-defer';p.mkdir(exist_ok=True);(p/'main.cpp').write_text(s);(p/'README.md').write_text('改良元: `solutions/deval-seven-wide`\n\n窓割り当てで、変更対象外の辺だけで8組全てに長さ2の閉路がある場合は、その組の新しい関係をまだ作らず費用をゼロにする。変更が採用されたときだけ、保存した方向ビット集合から全組の関係を正確に更新する。互換性がないことが確定した組だけなので、目的値・候補順・乱数・固定予算は同じ。\n');print(len(s.encode()));assert len(s.encode())<=520000
