from pathlib import Path
R=Path(__file__).resolve().parents[2];B=(R/'solutions/dcomp-combo-alt1/main.cpp').read_text()
a='''    int npending = 0;
    for (int block = 0; block < P.words; ++block) {''';assert B.count(a)==1
s=B.replace(a,'''#if defined(__clang__)
    std::array<uint8_t,4096> compatible_groups;
#endif
'''+a)
a='''            _mm256_storeu_si256((__m256i*)(nrel + p), kept);''';assert s.count(a)==1
s=s.replace(a,a+'''
            compatible_groups[p>>3]=_mm256_movemask_ps(_mm256_castsi256_ps(_mm256_cmpgt_epi32(kept,zero)));''')
a='''    for (int k = 0; k < nacyclic; ++k) nrel[pending[k]] = 1 + relations.sums.both_of(closures[k]);''';assert s.count(a)==1
s=s.replace(a,'''    for (int k = 0; k < nacyclic; ++k) {
        const int p=pending[k];nrel[p]=1+relations.sums.both_of(closures[k]);
#if defined(__clang__)
        compatible_groups[p>>3]|=uint8_t(1U<<(p&7));
#endif
    }''')
a='''        const __m256i rel4 = _mm256_loadu_si256((const __m256i*)(nrel + p));
        const int good = _mm256_movemask_ps(_mm256_castsi256_ps(_mm256_cmpgt_epi32(rel4, zero)));''';assert s.count(a)==1
s=s.replace(a,'''        // Kept compatibility was already known in the SIMD update. New acyclic
        // pairs set their bits during lookup, avoiding a second full nrel scan.
        const int good=compatible_groups[p>>3];''')
d=R/'solutions/dcomp-t11-validmask';assert not d.exists();d.mkdir();(d/'main.cpp').write_text(s)
(d/'README.md').write_text('改良元: solutions/dcomp-combo-alt1\n\nClangのdense valid列挙でnrel配列を再度load・比較する代わりに、SIMD更新時点で得た8laneのcompatible maskを保存する。新しくacyclicと判定されたpairだけbitを加え、元と同じ順で圧縮する。GCCは既存の疎な経路を保つ。\n\n探索予算・候補順・lookup順・算術は変更しない。両コンパイラで同じ予算を使用する。ログ・trace・profiler・実験スイッチ・目次と段・DesignStoreを保持する。\n')
