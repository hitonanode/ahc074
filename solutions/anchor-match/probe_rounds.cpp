#include "common.hpp"
#include "matching.hpp"
#include "head.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int seqs=argc>3?std::stoi(argv[3]):16,rounds=argc>4?std::stoi(argv[4]):8;
 auto initial=recover(*base);
 double reference=0;std::cout<<std::setprecision(12)<<"[";bool first=true;
 std::vector<int>roundlist{0,1,2,4,8};for(int count:roundlist){double weight=count?1.:0.;
  auto d=*initial;auto stats=weight?rematch_head(d,count,weight):MatchStats{};Solver s=*base;materialize(s,d);auto state=s.save();long long total=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  double avg=double(total)/(seqs*1024);if(!weight)reference=avg;
  std::cout<<(first?"":",")<<"{\"rounds\":"<<count<<",\"weight\":"<<weight<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"model\":"<<d.cur/P<<",\"decrease\":"<<stats.decrease<<",\"cycles\":"<<stats.accepted_cycles<<",\"changed\":"<<stats.changed<<",\"match_seconds\":"<<stats.seconds<<",\"seconds\":"<<elapsed_sec()<<"}"<<std::flush;first=false;
 }
 std::cout<<"]\n";
}
