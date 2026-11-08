from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
x='''    const __m128i shift_a = _mm_cvtsi32_si128(__builtin_ctzll(fa));''';assert B.count(x)==1
for name,code in [('dircompact','''    static const auto compact=[] {
        std::array<u64,256> out{};
        for(int m=0;m<256;++m)for(int l=0;l<8;++l)out[m]|=u64((m>>l)&1)<<(8*l);
        return out;
    }();
    auto unpack=[&](unsigned m) AVX2_TARGET {return _mm256_cvtepu8_epi32(_mm_loadl_epi64((const __m128i*)&compact[m]));};
'''),('dirpdep','''    auto unpack=[](unsigned m) AVX2_TARGET {return _mm256_cvtepu8_epi32(_mm_cvtsi64_si128(_pdep_u64(m,0x0101010101010101ULL)));};
'''),('dirmask','''    const auto flagbits=_mm256_setr_epi32(1,2,4,8,16,32,64,128);
    auto unpack=[&](unsigned m) AVX2_TARGET {return _mm256_and_si256(_mm256_cmpeq_epi32(_mm256_and_si256(_mm256_set1_epi32(m),flagbits),flagbits),_mm256_set1_epi32(1));};
''')]:
 s=B.replace(x,code+x)
 for v in ['a_fwd','a_rev','b_fwd','b_rev']:
  old=f'_mm256_load_si256((const __m256i*)directions[{v} & 255].data())';assert s.count(old)==1
  s=s.replace(old,f'unpack({v} & 255)')
 d=R/'solutions'/('dcomp-t11-'+name);assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
 (d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\nwindow evaluate_moveの8lane方向flag展開を '+name+' へ変更する出力同一の試験。元の32bit×8表に対し、8bit×8表のzero extend、PDEPで各byteへ散布してzero extend、定数bitとのSIMD比較のいずれかを使う。lane値は元の0/1と完全に同じ。\n\nprofileでmapの約24%を占めたSIMD段の表容量・依存関係を短縮する。固定予算・候補順・計算式・ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
