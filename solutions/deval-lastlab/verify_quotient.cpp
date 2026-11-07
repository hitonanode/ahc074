// Arithmetic component check only, RCP and reciprocal-table seeds: no AHC solver, inputs, or request planning.
#include <immintrin.h>
#include <bit>
#include <cstdint>
#include <cstdio>
__attribute__((target("avx2,fma"))) int verify() {
    std::uint64_t wrong=0,checked=0;
    const __m256 one=_mm256_set1_ps(1.f);
    alignas(32) float input[8],old[8],out[8],table_out[8];
    for(int d=1;d<=768;++d)for(int a=0;a<=65536;a+=8) {
        for(int j=0;j<8;++j)input[j]=float(a+j);
        const auto n=_mm256_load_ps(input),den=_mm256_set1_ps(float(d));
        const auto r0=_mm256_rcp_ps(den);
        const auto r=_mm256_fmadd_ps(r0,_mm256_fnmadd_ps(den,r0,one),r0);
        const auto q=_mm256_mul_ps(n,r);
        const auto z=_mm256_fmadd_ps(r,_mm256_fnmadd_ps(q,den,n),q);
        _mm256_store_ps(old,_mm256_div_ps(n,den));_mm256_store_ps(out,z);
        const auto tr=_mm256_set1_ps(1.f/d),tq=_mm256_mul_ps(n,tr);
        _mm256_store_ps(table_out,_mm256_fmadd_ps(tr,_mm256_fnmadd_ps(tq,den,n),tq));
        for(int j=0;j<8 && a+j<=65536;++j) {
            ++checked;
            if(std::bit_cast<std::uint32_t>(old[j])!=std::bit_cast<std::uint32_t>(out[j]) || std::bit_cast<std::uint32_t>(old[j])!=std::bit_cast<std::uint32_t>(table_out[j])) {
                if(wrong<8)std::printf("mismatch %d / %d: %a %a\n",a+j,d,double(old[j]),double(out[j]));
                ++wrong;
            }
        }
    }
    std::printf("checked = %llu\nwrong = %llu\n",(unsigned long long)checked,(unsigned long long)wrong);
    return wrong?1:0;
}
int main(){return verify();}
