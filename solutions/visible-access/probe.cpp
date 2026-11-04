#include "saved.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;int seqs=argc>3?std::stoi(argv[3]):8;
 base->init_adaptive();base->comparator.build_tables();base->interleave=std::make_shared<Interleave>();base->interleave->init(base->comparator,base->paper,base->A,base->ded,base->col_of,base->gmask,base->hmask,1e9);base->init_lookahead();
 double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<3;mode++){
  Solver s=*base;Solver::visible_access_mode=mode;auto initial=s.save();long long total=0,wrong=0;
  for(int q=0;q<seqs;q++){s.restore(initial);std::mt19937_64 rng(190000009ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;total+=s.process(u).size();wrong+=s.display()!=s.A[u];}}
  double average=double(total)/(seqs*1024);if(!mode)reference=average;std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<average<<",\"difference\":"<<average-reference<<",\"wrong\":"<<wrong<<",\"alternate_trials\":"<<s.alternate_accesses<<",\"alternate_depth\":"<<s.alternate_depth<<"}"<<std::flush;
 }std::cout<<"]\n";
}
