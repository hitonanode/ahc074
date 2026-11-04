#include "common.hpp"
#include "price.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int seqs=argc>3?std::stoi(argv[3]):8,iters=argc>4?std::stoi(argv[4]):20000000;
 auto initial_design=recover(*base);base->comparator.build_tables();double reference=0;bool first=true;std::cout<<std::setprecision(12)<<"[";
 for(double weight:{0.,.5,1.}){
  auto d=*initial_design;auto start=std::chrono::steady_clock::now();GenericPrice pricing(base->comparator,d);
  if(weight)d.repricer=[&](Design& d){pricing.update(d,weight);};
  d.anneal(1e9,iters);d.filler_climb(1e9,65000);double design_time=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
  Solver s=*base;materialize(s,d);auto state=s.save();long long total=0,wrong=0,generic=0;
  for(int q=0;q<seqs;q++){s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto moves=s.process(u);total+=moves.size();for(auto[k,depth]:moves)generic+=k<6;wrong+=s.display()!=s.A[u];}}
  double avg=double(total)/(seqs*1024);if(!weight)reference=avg;
  std::cout<<(first?"":",")<<"{\"weight\":"<<weight<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"generic\":"<<double(generic)/(seqs*1024)<<",\"model\":"<<d.cur/P<<",\"design_seconds\":"<<design_time<<",\"price_seconds\":"<<pricing.seconds<<",\"price_spread\":"<<pricing.spread<<",\"lower\":"<<pricing.lower<<",\"upper\":"<<pricing.upper<<",\"iterations\":"<<pricing.iterations<<",\"events\":"<<pricing.events.size()<<",\"pairs\":"<<pricing.pairs.size()<<",\"seconds\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}"<<std::flush;first=false;
 }std::cout<<"]\n";
}
