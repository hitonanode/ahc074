#include "common.hpp"
#include "../anchor-match/matching.hpp"
#include "prob.hpp"
int main(int argc,char**argv){auto base=head::load(argv[1],argv[2]);auto d=recover(*base);d->refresh_reset();Design::correlation_strength=1;ProbabilityHead model(*d,2,true);int checked=0;
 for(int a=0;a<d->H-1;a++)for(int b=a+1;b<d->H-1;b++)for(int bits=0;bits<4;bits++){
  u64 tb=(u64(bits&1)<<a)|(u64(bits>>1)<<b),dy=low_bits(d->H-1)&~((1ULL<<a)|(1ULL<<b));std::array<double,26>q{};
  for(int j=0;j<d->H;j++)q[j+1]=q[j]+2*model.prob[j][(tb>>j&1)^1];
  double got=Design::filler_gain(tb,-1,0,tb,dy,d->H-1,q.data()),cov=Design::head_covariance[a][b]*(((tb>>a)^(tb>>b))&1?-1:1),expected=.4*(model.prob[a][(tb>>a&1)^1]*model.prob[b][(tb>>b&1)^1]+cov);
  assert(std::abs(got-expected)<1e-8);checked++;
 }
 std::mt19937_64 rng(9018221);std::vector<u64>events(P);for(int t=0;t<P;t++)events[t]=d->holes(d->unit[d->owner[t]]);
 u64 state=0;std::array<double,25>sum{};std::array<std::array<double,25>,25>joint{};int samples=0;
 for(int it=0;it<1010000;it++){
  int e=rng()%(3*P);if(e<P)state=(state&~events[e])|(d->hb[e]&events[e]);else{int c=d->unit[d->owner[(e-P)%P]].c;state&=~(1ULL<<c);if(d->hn[c][1]>d->hn[c][0])state|=1ULL<<c;}
  if(it>=10000&&it%8==0){samples++;for(int a=0;a<d->H;a++){sum[a]+=state>>a&1;for(int b=a+1;b<d->H;b++)joint[a][b]+=int(state>>a&1)*int(state>>b&1);}}
 }
 double maximum=0,rmse=0;int count=0;
 for(int a=0;a<d->H;a++)for(int b=a+1;b<d->H;b++){double empirical=joint[a][b]/samples-(sum[a]/samples)*(sum[b]/samples),delta=empirical-Design::head_covariance[a][b];maximum=std::max(maximum,std::abs(delta));rmse+=delta*delta;count++;}
 assert(maximum<.01);std::cout<<checked<<" two-bit gains match exact joint probabilities; covariance RMSE="<<std::sqrt(rmse/count)<<" max="<<maximum<<'\n';
}
