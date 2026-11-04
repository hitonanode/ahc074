#include "common.hpp"

int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int seqs=argc>3?std::stoi(argv[3]):8;
 auto initial_design=recover(*base);initial_design->filler_climb(1e9,65000);
 double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(double weight:{0.,.05,.1,.2,.4,.8}){
  auto d=*initial_design;Solver::rank_reward_strength=weight;auto start=std::chrono::steady_clock::now();
  Solver s=*base;materialize(s,d);auto state=s.save();long long total=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  double avg=double(total)/(seqs*1024);if(!weight)reference=avg;
  std::cout<<(weight?",":"")<<"{\"weight\":"<<weight<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"seconds\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}"<<std::flush;
 }std::cout<<"]\n";
}
