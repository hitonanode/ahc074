#include "common.hpp"
#include "../anchor-match/matching.hpp"
#include "prob.hpp"
int main(int argc,char**argv){auto base=head::load(argv[1],argv[2]);auto d=recover(*base);d->refresh_reset();
 for(int strength:{0,2}){
  ProbabilityHead model(*d,strength,false);auto deriv=model.probability_gradient();const double eps=1e-6;
  for(int j=0;j<d->H;j++){
   auto saved=model.prob;auto update_q=[&](){for(int t=0;t<P;t++){model.q[t][0]=0;for(int c=0;c<d->H;c++)model.q[t][c+1]=model.q[t][c]+2*model.prob[c][(d->hb[t]>>c&1)^1];}};
   model.prob[j][1]+=eps;model.prob[j][0]-=eps;update_q();double plus=model.rebuild();model.prob=saved;model.prob[j][1]-=eps;model.prob[j][0]+=eps;update_q();double minus=model.rebuild();model.prob=saved;update_q();model.rebuild();
   double exact=(plus-minus)/(2*eps);assert(std::abs(exact-deriv[j])<1e-5);
  }
 }
 std::cout<<"50 probability derivatives match finite differences\n";
}
