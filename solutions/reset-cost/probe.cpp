#include "common.hpp"

int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int seqs=argc>3?std::stoi(argv[3]):8,iters=argc>4?std::stoi(argv[4]):20000000;
 auto initial_design=recover(*base);
 double reference=0;std::cout<<std::setprecision(12)<<"[";
 std::vector<double> weights=argc>5?std::vector<double>{std::stod(argv[5])}:std::vector<double>{0.,.5,1.,2.};
 bool first=true;for(double weight:weights){
  auto d=*initial_design;Design::reset_strength=weight;auto start=std::chrono::steady_clock::now();d.anneal(1e9,iters);d.filler_climb(1e9,65000);double design_time=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  Solver s=*base;materialize(s,d);auto state=s.save();long long total=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  double avg=double(total)/(seqs*1024);if(!weight)reference=avg;
  std::cout<<(first?"":",")<<"{\"weight\":"<<weight<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"model\":"<<d.cur/P<<",\"design_seconds\":"<<design_time<<",\"seconds\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}"<<std::flush;first=false;
 }std::cout<<"]\n";
}
