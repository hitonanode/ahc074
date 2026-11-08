"""Extract 32 validity bits per AVX2 compaction, then enumerate set bits."""
from pathlib import Path
root=Path(__file__).resolve().parents[2]
s=(root/'solutions/dcomp-nine/main.cpp').read_text()
a='''    int nvalid = 0;
    for (int p = 0; p < n8; p += 8) {
        const __m256i rel4 = _mm256_loadu_si256((const __m256i*)(nrel + p));
        const int good = _mm256_movemask_ps(_mm256_castsi256_ps(_mm256_cmpgt_epi32(rel4, zero)));
        _mm256_storeu_si256(
            (__m256i*)(valid + nvalid),
            _mm256_add_epi32(_mm256_set1_epi32(p), _mm256_loadu_si256((const __m256i*)lanes[good].data())));
        nvalid += __builtin_popcount(good);
    }'''
b='''    int nvalid=0,p=0;
    for(;p+31<n8;p+=32) {
        const __m256i a=_mm256_cmpgt_epi32(_mm256_loadu_si256((const __m256i*)(nrel+p)),zero);
        const __m256i b=_mm256_cmpgt_epi32(_mm256_loadu_si256((const __m256i*)(nrel+p+8)),zero);
        const __m256i c=_mm256_cmpgt_epi32(_mm256_loadu_si256((const __m256i*)(nrel+p+16)),zero);
        const __m256i d=_mm256_cmpgt_epi32(_mm256_loadu_si256((const __m256i*)(nrel+p+24)),zero);
        // Packs work inside 128-bit halves. Put the four-byte groups back in
        // pair-index order before extracting one bit per original int32 lane.
        const __m256i packed=_mm256_packs_epi16(_mm256_packs_epi32(a,b),_mm256_packs_epi32(c,d));
        const __m256i ordered=_mm256_permutevar8x32_epi32(packed,_mm256_setr_epi32(0,4,1,5,2,6,3,7));
        for(unsigned good=unsigned(_mm256_movemask_epi8(ordered));good;good&=good-1)
            valid[nvalid++]=p+__builtin_ctz(good);
    }
    for(;p<n8;p+=8) {
        const __m256i q=_mm256_loadu_si256((const __m256i*)(nrel+p));
        for(unsigned good=unsigned(_mm256_movemask_ps(_mm256_castsi256_ps(_mm256_cmpgt_epi32(q,zero))));good;good&=good-1)
            valid[nvalid++]=p+__builtin_ctz(good);
    }'''
assert s.count(a)==1
p=root/'solutions/dcomp-nine-valid32';p.mkdir(exist_ok=True)
(p/'main.cpp').write_text(s.replace(a,b))
(p/'README.md').write_text('''改良元: solutions/dcomp-nine

窓探索のrelation費用から互換ペアを列挙する段で、32個の正値判定をAVX2のpackで32bitに圧縮し、立っているbitだけを昇順に列挙する。128bit lane内pack後の順序を明示的に並べ直す。8個ごとに候補一覧へ32byte書く処理を省く。末尾の8個単位も同じ順序で列挙する。

relation配列や探索状態は元のままで、互換一覧の値と順序も不変。乱数、固定反復数、9候補、浮動小数点評価、注文処理、ログ、CLOCK_SCALE、実験スイッチ・プロファイラを保持。時間不足の切替なし。
''')
