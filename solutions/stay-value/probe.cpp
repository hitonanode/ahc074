#include "common.hpp"
int main(int argc,char**argv) {
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto d=recover(*base);materialize(*base,*d);
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;
 std::cout<<std::setprecision(12)<<"[";
 int mode=0;
 for(auto[stay,cover]:std::array<std::pair<double,double>,7>{{{0,0},{.5,0},{1,0},{0,.25},{0,.5},{.25,.25},{.5,.5}}}) {
  Solver::stay_strength=stay;Solver::cover_strength=cover;
  Solver s=*base;auto initial=s.save();
  long long total=0,wrong=0;double start=elapsed_sec();
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
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode++<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"stay\":"<<stay<<",\"cover\":"<<cover<<",\"seconds\":"<<(elapsed_sec()-start)/sequences<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
