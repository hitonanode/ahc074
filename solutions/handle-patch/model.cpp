#include "design.hpp"
int main(int argc,char**argv){if(argc<6)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;auto original=recover(*base);u64 bits=std::stoull(argv[3]),color=std::stoull(argv[4]);int h=std::stoi(argv[5]),iterations=argc>6?std::stoi(argv[6]):10000000;
 u64 physical=0,black=0;for(int j=0;j<original->H;j++){if(bits>>j&1)physical|=1ULL<<original->handle[j];if(color>>j&1)black|=1ULL<<original->handle[j];}double reference=0;std::cout<<std::setprecision(12)<<"[";
 for(int kind=0;kind<3;kind++){
  Problem p(*original,-1);if(kind){p.patch_mask=physical;p.patch_color=black;p.patch_handle=original->handle[h];p.patch_fee=kind==1?1.6:2;}
  Search s(p);if(!s.initialize(0))return 4;s.optimize(iterations);double saved=s.current;s.rebuild();assert(std::abs(saved-s.current)<1e-6);double value=s.current/P;if(!kind)reference=value;int selected=0;double plain=0;
  for(auto u:s.units){auto g=s.groups[u.group];assert(s.valid(u.group,u.column));if(g.patched){selected++;assert(!((p.A[g.a[1]]^p.patch_color)&(p.patch_mask|(1ULL<<p.patch_handle))));}else plain+=g.n;}
  std::cout<<(kind?",":"")<<"{\"kind\":"<<kind<<",\"model\":"<<value<<",\"difference\":"<<value-reference<<",\"selected\":"<<selected<<",\"seconds\":"<<elapsed_sec()<<"}"<<std::flush;
 }
 std::cout<<"]\n";
}
