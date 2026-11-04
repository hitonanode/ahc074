#ifdef BASELINE
#include "../head-design/saved.hpp"
#else
#include "saved.hpp"
#endif
int main(int argc,char**argv){
 if(argc<3)return 2;auto ptr=head::load(argv[1],argv[2]);if(!ptr)return 3;Solver&s=*ptr;int seqs=argc>3?std::stoi(argv[3]):8;
 s.init_adaptive();s.comparator.build_tables();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
#ifndef BASELINE
 s.init_front();std::cerr<<"front_lower = "<<s.front->lower<<"\nfront_upper = "<<s.front->upper<<"\nfront_seconds = "<<s.front->seconds<<"\n";
#endif
 auto state=s.save();long long total=0,wrong=0;auto start=std::chrono::steady_clock::now();
 for(int q=0;q<seqs;q++){s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;for(int t=0;t<1024;t++){int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
#ifndef BASELINE
s.front_debug=q==9&&t==180;
if(s.front_debug){std::cerr<<"before top "<<s.top_d<<" target "<<s.ded[u]<<"\n";for(auto f:s.fillers)std::cerr<<"filler "<<f.paper<<" "<<f.lvl<<" "<<f.hi<<"\n";for(int k:s.front_papers)std::cerr<<"front "<<k<<" "<<s.h_opq[k]<<" "<<s.h_blk[k]<<"\n";}
#endif
auto moves=s.process(u);total+=moves.size();wrong+=s.display()!=s.A[u];
#ifndef BASELINE
  if(s.display()!=s.A[u]||!s.front_invariant()){std::cerr<<"Failure "<<q<<" "<<t<<" "<<u<<" top "<<s.top_d<<" failures "<<s.plan_failures<<"\n";for(int k:s.order)std::cerr<<k<<" ";std::cerr<<"\n";return 4;}
#endif
 }}
 std::cout<<std::setprecision(12)<<"{\"moves\":"<<double(total)/(seqs*1024)<<",\"wrong\":"<<wrong<<",\"failures\":"<<s.plan_failures<<",\"seconds\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";
}
