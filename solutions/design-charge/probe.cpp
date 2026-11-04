#include "common.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto old=recover(*base);old->anneal(1e9,20000000);int sequences=argc>3?std::stoi(argv[3]):16;
 int iterations=argc>4?std::stoi(argv[4]):20000000;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<4;mode++){
  Design::design_return_cost=std::array<double,4>{.6,.4,.8,1}[mode];
  auto d=*old;d.refresh_reset();double start=elapsed_sec();d.filler_climb(1e9,65000);rematch_probability(d,4,1,2,true,true);d.refresh_reset();
  double before=d.cur;d.rebuild();assert(std::abs(before-d.cur)<1e-6);
  ProbabilityHead head(d,2,true);double merit=(d.cur-head.rebuild())/P;
  Solver s=*base;materialize(s,d);s.init_handle_cache();Perforation p(s);p.run(.5,1,false);p.install();
  s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
  double design_seconds=elapsed_sec()-start;auto initial=s.save();long long total=0,wrong=0;
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   }
  }
  assert(!wrong);assert(!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"model\":"<<d.cur/P<<",\"merit\":"<<merit<<",\"design_seconds\":"<<design_seconds<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
