#include "common.hpp"
int main(int argc,char**argv) {
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto d=recover(*base);materialize(*base,*d);
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;
 std::cout<<std::setprecision(12)<<"[";
 int mode=0;
 for(int config=0;config<4;config++) {
  int rewrite=(config==1||config==2)?2:0;Solver::post_compact=config>=2;
  Solver::post_rewrite_mode=rewrite;Solver s=*base;auto initial=s.save();
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
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode++<<",\"count\":"<<2<<",\"joint\":"<<rewrite<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"pair_trials\":"<<double(s.rewrite_trials)/sequences<<",\"pair_accepts\":"<<double(s.rewrite_accepts)/sequences<<",\"same_column\":"<<double(s.rewrite_same_column)/sequences<<",\"same_paper\":"<<double(s.rewrite_same_paper)/sequences<<",\"compact_fallback\":"<<double(s.compact_fallback)/sequences<<",\"nodes\":"<<double(s.compact_nodes)/s.post_candidate_calls<<",\"seconds\":"<<(elapsed_sec()-start)/sequences<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
