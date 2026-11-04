#include "common.hpp"
int main(int argc,char**argv) {
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto d=recover(*base);int sequences=argc>3?std::stoi(argv[3]):16;
 double reference=0;int mode=0;std::cout<<std::setprecision(12)<<"[";
 for(auto [reset,weight]:std::vector<std::pair<double,double>>{{0,.25},{2,.25},{2,.5},{1,.25},{4,.25},{2,1}}) {
  Solver::return_reset_strength=reset;Solver::return_demand_weight=weight;
  Solver s=*base;materialize(s,*d);auto initial=s.save();long long total=0,wrong=0;
  double begin=elapsed_sec();
  for(int q=0;q<sequences;q++) {
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++) {
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
    auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0) {
     for(auto[k,depth]:path) {
      int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;
      for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;
      assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);
     }
     assert(before==s.order);
    }
   }
  }
  assert(!wrong);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode++<<",\"reset\":"<<reset<<",\"weight\":"<<weight<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"seconds\":"<<(elapsed_sec()-begin)/sequences<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
