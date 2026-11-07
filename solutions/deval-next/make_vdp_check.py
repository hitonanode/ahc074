from pathlib import Path
r=Path(__file__).resolve().parents[2];p=Path(__file__).resolve().parent
head='''#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <cmath>
#include <cstdint>
#include <vector>
#include <iostream>
#include <random>
#include <cstring>
#if defined(__GNUC__) && !defined(__clang__)
#pragma GCC optimize("O3")
#endif
'''
for name,ns in [('deval-seven-wide','reference'),('deval-vintdp','integer'),('deval-vskipdp','skip')]:
 s=(r/'solutions'/name/'main.cpp').read_text();a=s.index('namespace deval {\nusing U64');b=s.index('} // namespace deval',a)+len('} // namespace deval')
 head+=s[a:b].replace('namespace deval {','namespace '+ns+' {')+'\n'
head+='''int main(){
 std::mt19937_64 rng(987123);
 for(int trial=0;trial<256;++trial){
  reference::State s;s.H=trial%3==0?25:trial%3==1?31:35;
  for(int c=0;c<s.H;++c)s.handle[c]=c;
  for(int k=0;k<192;++k){
   s.col[k]=k<7?-1:(k-7)%s.H;
   if(k<7)continue;
   int c=s.col[k];uint64_t own=uint64_t(1)<<c;
   s.opaque[k]=reference::low(c+1)&~(rng()&rng()&rng());s.opaque[k]|=own;
   s.black[k]=(rng()&s.opaque[k]&~own)|(((k-7)/s.H%2)?own:0);
  }
  for(int t=0;t<256;++t){s.target[t]=rng();s.ded[t]=7+t%185;}
  s.prepare();
  std::array<double,reference::MaxH> prob;
  for(int c=0;c<s.H;++c)prob[c]=trial%13==0?double(c%2):double(rng()>>11)*0x1p-53;
  std::array<double,16*35> draws;
  for(auto& x:draws)x=double(rng()>>11)*0x1p-53;
  const auto si=std::bit_cast<integer::State>(s),ss=std::bit_cast<skip::State>(s);
  const reference::Donors dr(s,prob);const integer::Donors di(si,prob);const skip::Donors ds(ss,prob);
  const auto a=reference::expectation(s,dr,prob,draws.data(),16,1.6);
  const auto b=integer::expectation(si,di,prob,draws.data(),16,1.6);
  const auto c=skip::expectation(ss,ds,prob,draws.data(),16,1.6);
  if(std::memcmp(&a,&b,sizeof(a)) || std::memcmp(&a,&c,sizeof(a))){std::cerr<<"mismatch trial="<<trial<<"\\n";return 1;}
 }
 std::cout<<"256 synthetic designs, 1048576 target/sample DPs: bit-identical target features and flip rates\\n";
}
'''
# Separate declarations because their state types differ.
head=head.replace('const auto si=std::bit_cast<integer::State>(s),ss=std::bit_cast<skip::State>(s);','const auto si=std::bit_cast<integer::State>(s);const auto ss=std::bit_cast<skip::State>(s);')
(p/'vdp_check.cpp').write_text(head)
