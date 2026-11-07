#include <immintrin.h>
#include <cstdio>
#include <bit>
#include <cstdint>
#include <algorithm>
__attribute__((target("avx2,fma"))) int main_test(){
 const auto one=_mm256_set1_ps(1.f); long long tested=0;
 for(int nt=0;nt<=256;++nt)for(int a=0;a<=256;++a)for(int b=0;b<=256;b+=8){
  auto aa=_mm256_set1_ps(float(a)),bb=_mm256_setr_ps(float(b),float(b+1),float(b+2),float(b+3),float(b+4),float(b+5),float(b+6),float(b+7));
  auto n=_mm256_fmadd_ps(_mm256_set1_ps(float(nt)),_mm256_min_ps(aa,bb),_mm256_mul_ps(aa,bb));
  auto den=_mm256_max_ps(_mm256_add_ps(_mm256_add_ps(aa,bb),_mm256_set1_ps(2.f*nt)),one);
  auto r=_mm256_rcp_ps(den);r=_mm256_fmadd_ps(_mm256_fnmadd_ps(r,den,one),r,r);
  auto q=_mm256_mul_ps(n,r);q=_mm256_fmadd_ps(_mm256_fnmadd_ps(q,den,n),r,q);
  auto ref=_mm256_div_ps(n,den);
  alignas(32) float x[8],y[8];_mm256_store_ps(x,q);_mm256_store_ps(y,ref);
  for(int i=0;i<8&&b+i<=256;++i){++tested;if(std::bit_cast<uint32_t>(x[i])!=std::bit_cast<uint32_t>(y[i])){std::printf("FAIL nt=%d a=%d b=%d %a %a\n",nt,a,b+i,x[i],y[i]);return 1;}}
 }
 std::printf("PASS %lld reachable count combinations\n",tested);return 0;
}
int main(){return main_test();}
