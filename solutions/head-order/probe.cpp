#include "common.hpp"
#include "../anchor-match/matching.hpp"
#include "../head-prob/prob.hpp"
#include "order.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto initial=recover(*base);initial->anneal(1e9,20000000);initial->filler_climb(1e9,65000);rematch_probability(*initial,4,1,2,true,true);
 int seqs=argc>3?std::stoi(argv[3]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<4;mode++){
  auto d=*initial;auto stats=mode?order_head(d,mode==1?1:4,mode==3?4:1):OrderStats{};
  Solver s=*base;materialize(s,d);auto state=s.save();long long total=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  assert(!wrong);double avg=double(total)/(seqs*1024);if(!mode)reference=avg;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"decrease\":"<<stats.change<<",\"trials\":"<<stats.trials<<",\"accepted\":"<<stats.accepted<<",\"match_seconds\":"<<stats.seconds<<",\"seconds\":"<<elapsed_sec()<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
