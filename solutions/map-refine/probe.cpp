#include "common.hpp"
#include "search.hpp"
double improve(Design&d,int iterations){
 d.anneal(1e9,iterations);d.filler_climb(1e9,15000);rematch_probability(d,2,1,2,true,true);d.refresh_reset();
 ProbabilityHead h(d,2,true);return (d.cur-h.rebuild())/P;
}
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto old=recover(*base);old->refresh_reset();int sequences=argc>3?std::stoi(argv[3]):16;
 int iterations=argc>4?std::stoi(argv[4]):1000000;
 auto d0=*old;double start=elapsed_sec(),before=improve(d0,iterations);
 auto d1=d0;auto comp=base->comparator;int viable=0,repaired=0,chosen=-1;
 auto list=candidates(*old,comp,6,viable,repaired);double best=before;
 for(int i=0;i<int(list.size());i++){
  auto&x=list[i];auto c=base->comparator;c.polarity[x.j]^=x.flip;c.rebuild();
  complete_prices(*x.d,c);double merit=improve(*x.d,iterations);
  if(merit<best-1e-8){best=merit;d1=*x.d;comp=c;chosen=i;}
 }
 double seconds=elapsed_sec()-start;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<2;mode++){
  auto d=mode?d1:d0;Solver s=*base;s.A=d.A;for(int u=0;u<P;u++)s.A[u]|=base->A[u]&kCapBit;
  s.comparator=mode?comp:base->comparator;for(int k=0;k<6;k++)s.paper[k]={s.comparator.opq[k],s.comparator.black[k]};
  s.handle_cache_ready=false;materialize(s,d);s.init_handle_cache();Perforation p(s);p.run(.5,1,false);p.install();
  s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
  auto initial=s.save();long long total=0,wrong=0;
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(75100000019ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto order=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0){for(auto[k,depth]:path){int at=std::find(order.begin(),order.end(),k)-order.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[order[j]].opaque;assert(s.paper[k].opaque&~seen);order.erase(order.begin()+at);order.insert(order.begin()+depth,k);}assert(order==s.order);}
   }
  }
  assert(!wrong&&!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"viable\":"<<viable<<",\"candidates\":"<<list.size()<<",\"chosen\":"<<chosen<<",\"model\":"<<(mode?best:before)<<",\"seconds\":"<<seconds<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
