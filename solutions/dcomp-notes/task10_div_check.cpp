// Numeric analysis only: all integer hole counts in [0,256], both compilers.
#include <immintrin.h>
#include <bit>
#include <cstdint>
#include <cstdio>
#include <algorithm>
int main(){
    const __m256 one=_mm256_set1_ps(1.f),half=_mm256_set1_ps(.5f);
    alignas(32) float b[8],orig[8],fast[8];
    long long tested=0,bad=0;
    for(int i=0;i<=256;++i)for(int j=0;j<=256;j+=8)for(int k=0;k<=256;++k){
        for(int l=0;l<8;++l)b[l]=j+l;
        const auto x=_mm256_set1_ps(i),y=_mm256_load_ps(b),z=_mm256_set1_ps(k);
        const auto s=_mm256_max_ps(_mm256_add_ps(_mm256_add_ps(x,y),z),one);
        const auto n=_mm256_fmadd_ps(_mm256_mul_ps(half,z),_mm256_min_ps(x,y),_mm256_mul_ps(x,y));
        const auto r0=_mm256_rcp_ps(s);
        const auto r=_mm256_fmadd_ps(r0,_mm256_fnmadd_ps(s,r0,one),r0);
        const auto q=_mm256_mul_ps(n,r);
        const auto f=_mm256_fmadd_ps(_mm256_fnmadd_ps(q,s,n),r,q);
        _mm256_store_ps(orig,_mm256_div_ps(n,s));_mm256_store_ps(fast,f);
        for(int l=0;l<8 && j+l<=256;++l){++tested;if(std::bit_cast<uint32_t>(orig[l])!=std::bit_cast<uint32_t>(fast[l])){if(bad<10)std::printf("bad %d %d %d %.9g %.9g\n",i,j+l,k,orig[l],fast[l]);++bad;}}
    }
    std::printf("tested=%lld mismatch=%lld\n",tested,bad);return bad?1:0;
}
