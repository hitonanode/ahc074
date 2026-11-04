#include "common.hpp"
#include "matching.hpp"
#include "prob.hpp"
#include "search.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto original=recover(*base);original->refresh_reset();int sequences=argc>3?std::stoi(argv[3]):16;
 double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<3;mode++){
  auto d=*original;auto comp=base->comparator;SwapStats stats;
  if(mode)stats=optimize_swaps(d,comp,mode,4);
  d.anneal(1e9,1000000);d.filler_climb(1e9,15000);rematch_probability(d,2,1,2,true,true);d.refresh_reset();
  for(auto u:d.unit){assert(d.valid(u,u.c));if(u.b>=0)assert(comp.compatible(d.A[u.a],d.A[u.b]));}
  Solver s=*base;s.A=d.A;for(int u=0;u<P;u++)s.A[u]|=base->A[u]&kCapBit;s.comparator=comp;
  for(int k=0;k<6;k++)s.paper[k]={comp.opq[k],comp.black[k]};
  materialize(s,d);Perforation p(s);p.run(.5,1,false);p.install();
  s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
  auto initial=s.save();long long total=0,wrong=0;
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   }
  }
  assert(!wrong);assert(!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"viable\":"<<stats.viable<<",\"accepted\":"<<stats.accepted<<",\"model_decrease\":"<<stats.decrease<<",\"seconds\":"<<stats.seconds<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
