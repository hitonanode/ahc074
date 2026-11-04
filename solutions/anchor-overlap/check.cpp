#include "common.hpp"
#include "../anchor-match/matching.hpp"
#include "../anchor-match/head.hpp"
#include "model.hpp"
int main(int argc,char**argv){auto base=head::load(argv[1],argv[2]);auto d=recover(*base);d->refresh_reset();OverlapModel m(*d,8);double old=m.rebuild(true);m.check();int tested=0;
 for(int x=0;x<d->U&&tested<12;x++)if(m.simple.beta[x]){
  auto u=d->unit[x];int b=d->color(u,u.c);u.a=(u.a+53)%P;while(int(d->hb[u.a]>>u.c&1)!=b)u.a=(u.a+1)%P;u.b=-1;
  double predicted=m.donor(u,x);auto op=m.opaque[x],bl=m.black[x];m.opaque[x]=low_bits(u.c+1);m.black[x]=d->hb[u.a];double exact=0;
  for(int t=0;t<P;t++)for(int s=0;s<m.copies;s++)exact+=m.solve(m.edges(t,d->holes(d->unit[d->owner[t]]),m.samples[t*m.copies+s],d->unit[d->owner[t]].c));
  exact=exact/m.copies-old;assert(std::abs(exact-predicted)<1e-7);m.opaque[x]=op;m.black[x]=bl;tested++;
 }
 std::cout<<tested<<" replacements match full DP\n";
}
