#include "common.hpp"
double merit(Design&d){d.refresh_reset();ProbabilityHead h(d,2,true);return (d.cur-h.rebuild())/P;}
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto old=recover(*base);old->anneal(1e9,20000000);old->filler_climb(1e9,65000);rematch_probability(*old,4,1,2,true,true);double initial=merit(*old);
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<4;mode++){
  auto d=*old;double best=initial,start=elapsed_sec();int accepted=0;
  if(mode){
   auto current=d;int rounds=mode==3?3:1,iterations=mode==1?500000:mode==2?1000000:250000;
   for(int r=0;r<rounds;r++){
    current.refresh_reset();Design::Annealer<4>(current).run(1e9,iterations,mode==2?.7:.85,1.15);
    current.filler_climb(1e9,15000);rematch_probability(current,2,1,2,true,true);
    double value=merit(current);if(value<best-1e-8){best=value;d=current;accepted++;}
   }
  }
  double seconds=elapsed_sec()-start;Solver s=*base;materialize(s,d);s.init_handle_cache();Perforation p(s);p.run(.5,1,false);p.install();
  s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
  auto initial_state=s.save();long long total=0,wrong=0;
  for(int q=0;q<sequences;q++){
   s.restore(initial_state);std::mt19937_64 rng(83310000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0){for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);}
   }
  }
  assert(!wrong&&!s.plan_failures);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"model\":"<<best<<",\"model_change\":"<<best-initial<<",\"accepted\":"<<accepted<<",\"seconds\":"<<seconds<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
