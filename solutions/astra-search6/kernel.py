"""既存の全対更新をassign_windows内だけで特殊化する。"""
def kernel(t, base, mode):
 a=base.index('AVX2_TARGET int evaluate_move(');b=base.index('\n}\n',a)+2
 k=base[a:b].replace('AVX2_TARGET int evaluate_move(', '    auto evaluate_fast = []<bool TwoEdges>(')
 k=k.replace('int* pending) {', 'int* pending) __attribute__((target("avx2,popcnt"))) {');k=k[:-1]+'};'
 if mode in ('branch','gatherbranch'):
  k=k.replace('''            _mm256_storeu_si256((__m256i*)(pending + npending),''', '''            if (need) _mm256_storeu_si256((__m256i*)(pending + npending),''')
  k=k.replace('''        _mm256_storeu_si256((__m256i*)(valid + nvalid),''', '''        if (good) _mm256_storeu_si256((__m256i*)(valid + nvalid),''')
 if mode=='noprefetch':
  k=k.replace('        if (k + 8 < npending) relations.prefetch(uint32_t(ndir[pending[k + 8]]));\n','')
 if mode in ('gather','gatherbranch'):
  a=k.index('    for (int k = 0; k < npending; ++k) {');b=k.index('    int nvalid = 0;',a)
  k=k[:a]+r'''    // Resolve four independent exact-cache lookups together. A cache miss still uses
    // the original closure routine; tag comparisons preserve correctness under collisions.
    int at = 0;
    alignas(32) u64 cached[4];
    for (; at+4 <= npending; at += 4) {
        const __m128i indices = _mm_loadu_si128((const __m128i*)(pending+at));
        const __m128i r = _mm_i32gather_epi32((const int*)ndir,indices,4);
        const __m128i rt = _mm_or_si128(_mm_srli_epi32(r,16),_mm_slli_epi32(r,16));
        const __m128i normal = _mm_min_epu32(r,rt);
        const __m128i hash = _mm_srli_epi32(_mm_mullo_epi32(
            _mm_xor_si128(normal,_mm_srli_epi32(normal,15)),_mm_set1_epi32(0x9e3779b1U)),32-WindowRelations::kCacheBits);
        const __m256i values = _mm256_i32gather_epi64((const long long*)relations.cache.data(),hash,8);
        const __m256i same = _mm256_cmpeq_epi64(_mm256_srli_epi64(values,32),_mm256_cvtepu32_epi64(normal));
        const int hit = _mm256_movemask_pd(_mm256_castsi256_pd(same));
        _mm256_store_si256((__m256i*)cached,values);
        for (int j = 0; j < 4; ++j) {
            const int p = pending[at+j];
            nrel[p] = (hit >> j & 1) ? uint32_t(cached[j]) : relations.cost(ndir[p]);
        }
    }
    for (; at < npending; ++at) {
        const int p = pending[at]; nrel[p] = relations.cost(ndir[p]);
    }
'''+k[b:]
 a=t.index('    auto propose =')
 t=t[:a]+k+'\n'+t[a:]
 a=t.index('    auto propose =')
 t=t[:a]+t[a:].replace('evaluate_move<','evaluate_fast.template operator()<')
 return t
