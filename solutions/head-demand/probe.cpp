#include "saved.hpp"
int main(int argc,char**argv){if(argc<3)return 2;int sequences=argc>3?std::stoi(argv[3]):8;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 base->init_adaptive();base->comparator.build_tables();base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();double reference=0;
 std::cout<<std::setprecision(12)<<"[";
 for(double strength:{0.,.25,.5,1.,2.}){
  Solver s=*base;s.add_filler_demand(strength);auto initial=s.save();long long total=0,wrong=0;
  for(int q=0;q<sequences;q++){s.restore(initial);std::mt19937_64 rng(110000003ULL*(q+1));int previous=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):previous;if(t&&u>=previous)u++;previous=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  double average=double(total)/(sequences*1024);if(strength==0)reference=average;
  std::cout<<(strength?",":"")<<"{\"strength\":"<<strength<<",\"moves\":"<<average<<",\"difference\":"<<average-reference<<",\"wrong\":"<<wrong<<",\"spread\":"<<s.filler_demand_spread<<"}"<<std::flush;
 }
 std::cout<<"]\n";return 0;}
