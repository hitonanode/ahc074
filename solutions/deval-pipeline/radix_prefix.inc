// Exclusive integer prefix sums for the two radix histograms. Each 128-bit
// half is scanned, then the lower half's sum is added to the upper half.
__attribute__((target("avx2"))) inline void radix_prefix(int* bins,int begin,int end) {
    int sum=0,i=begin;
    for(;i+8<=end;i+=8) {
        const auto original=_mm256_loadu_si256(reinterpret_cast<const __m256i*>(bins+i));
        auto v=_mm256_add_epi32(original,_mm256_slli_si256(original,4));
        v=_mm256_add_epi32(v,_mm256_slli_si256(v,8));
        const auto lo=_mm256_castsi256_si128(v);
        const auto hi=_mm_add_epi32(_mm256_extracti128_si256(v,1),_mm_shuffle_epi32(lo,255));
        v=_mm256_inserti128_si256(v,hi,1);
        const auto start=_mm256_add_epi32(_mm256_sub_epi32(v,original),_mm256_set1_epi32(sum));
        _mm256_storeu_si256(reinterpret_cast<__m256i*>(bins+i),start);
        sum+=_mm_extract_epi32(hi,3);
    }
    for(;i<end;++i){const int n=bins[i];bins[i]=sum;sum+=n;}
}

