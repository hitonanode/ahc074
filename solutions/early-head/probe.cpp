#include "common.hpp"
#define CHECK_LINEAR_PATH
#include "linear.hpp"

int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto initial=recover(*base);auto short_design=*initial,long_design=*initial;
 double start=elapsed_sec();short_design.anneal(1e9,10000000);double short_sec=elapsed_sec()-start;
 start=elapsed_sec();long_design.anneal(1e9,20000000);double long_sec=elapsed_sec()-start;
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;
 struct Setting{bool early;int rounds,steps;double weight,temperature;};
 std::vector<Setting> settings{{false,0,0,1,0},{true,1,50000,1,.1},{true,4,50000,1,.1},{true,2,200000,1,.4},{true,2,200000,1,1},{false,2,50000,1,.1},{true,2,50000,.5,.1}};
 std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<int(settings.size());mode++){
  auto setting=settings[mode];auto d=setting.early?short_design:long_design;start=elapsed_sec();
  LinearStats stats;
  if(setting.rounds)stats=optimize_linear(d,setting.rounds,setting.steps,setting.weight,setting.temperature);
  d.filler_climb(1e9,65000);rematch_probability(d,4,1,2,true,true);
  double seconds=elapsed_sec()-start+(setting.early?short_sec:long_sec);
  d.refresh_reset();ProbabilityHead head(d,2,true);double merit=(d.cur-head.rebuild())/P;
  Solver s=*base;materialize(s,d);auto state=s.save();long long total=0,wrong=0;
  for(int q=0;q<sequences;q++){
   s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
    auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(q==0){
     for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 covered=0;for(int j=0;j<at;j++)covered|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~covered);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}
     assert(before==s.order);
    }
   }
  }
  assert(!wrong);double value=double(total)/(sequences*1024);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"merit\":"<<merit<<",\"decrease\":"<<stats.decrease<<",\"cycles\":"<<stats.cycles<<",\"seconds\":"<<seconds<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
