#include "common.hpp"
#include "../anchor-match/matching.hpp"
#include "../anchor-match/head.hpp"
#include "prob.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto initial=recover(*base);
 int seqs=argc>3?std::stoi(argv[3]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<6;mode++){
  auto d=*initial;MatchStats stats;
  if(mode==0)stats=rematch_head(d,4,1);
  else if(mode==1)stats=rematch_probability(d,4,1,1,false,false);
  else if(mode==2)stats=rematch_probability(d,4,1,2,false,false);
  else if(mode==3)stats=rematch_probability(d,4,1,0,true,false);
  else if(mode==4)stats=rematch_probability(d,4,1,0,true,true);
  else if(mode==5)stats=rematch_probability(d,4,1,2,true,true);
  Solver s=*base;materialize(s,d);auto state=s.save();long long total=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  assert(!wrong);double avg=double(total)/(seqs*1024);if(!mode)reference=avg;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"decrease\":"<<stats.decrease<<",\"cycles\":"<<stats.accepted_cycles<<",\"changed\":"<<stats.changed<<",\"match_seconds\":"<<stats.seconds<<",\"seconds\":"<<elapsed_sec()<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
