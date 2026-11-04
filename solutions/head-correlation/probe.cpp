#include "common.hpp"
#include "../anchor-match/matching.hpp"
#include "prob.hpp"
int main(int argc,char**argv){if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto original=recover(*base);original->anneal(1e9,20000000);int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 int mode=0;for(double strength:{0.,.5,1.,2.}){Design::correlation_strength=strength;auto d=*original;double start=elapsed_sec();d.filler_climb(1e9,65000);auto stats=rematch_probability(d,4,1,2,true,true);double design_seconds=elapsed_sec()-start;Solver s=*base;materialize(s,d);auto initial=s.save();long long total=0,wrong=0;
  for(int q=0;q<sequences;q++){s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  assert(!wrong);double value=double(total)/(1024*sequences);if(!mode)reference=value;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode++<<",\"strength\":"<<strength<<",\"moves\":"<<value<<",\"difference\":"<<value-reference<<",\"wrong\":"<<wrong<<",\"decrease\":"<<stats.decrease<<",\"match_seconds\":"<<design_seconds<<",\"seconds\":"<<elapsed_sec()<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
