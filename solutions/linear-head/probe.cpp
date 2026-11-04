#include "common.hpp"
#include "linear.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto initial=recover(*base);initial->refresh_reset();
 int seqs=argc>3?std::stoi(argv[3]):16;double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<6;mode++){
  auto d=*initial;double start=elapsed_sec();LinearStats stats;
  if(mode)stats=optimize_linear(d,mode==4?3:1,50000,mode==1?.5:1.,mode==2?0:mode==5?.4:.1);
  double design_seconds=elapsed_sec()-start;
  Solver s=*base;materialize(s,d);auto state=s.save();long long total=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  assert(!wrong);double avg=double(total)/(seqs*1024);if(!mode)reference=avg;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"decrease\":"<<stats.decrease<<",\"accepted\":"<<stats.proposals<<",\"match_seconds\":"<<design_seconds<<",\"seconds\":"<<elapsed_sec()<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
