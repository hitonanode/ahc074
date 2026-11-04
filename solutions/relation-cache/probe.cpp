#define REL_CACHE_RESEARCH
#define main inherited_main
#include "main.cpp"
#undef main
#include <fstream>
#include <iomanip>
int main(int argc,char**argv){
 if(argc<2)return 2;std::ifstream in(argv[1]);int n,k,p,r;in>>n>>k>>p>>r;assert(n==64&&k==192&&p==256);
 std::vector<u64>original(P);for(auto&a:original){std::string text;in>>text;a=0;for(int j=0;j<63;j++)if(text[j]=='1')a|=1ULL<<j;}
 std::string name(argv[1]);int seed=std::stoi(name.substr(name.size()-8,4));std::array<int,4>bits{18,16,14,20};
 std::array<double,4>seconds{};u64 expected=0;
 for(int repeat=0;repeat<2;repeat++)for(int step=0;step<4;step++){
  int mode=(seed+step+repeat)%4;WindowRelations::kCacheBits=bits[mode];auto a=original;
  Comparator comp;std::mt19937_64 rng(779879);comp.init(6,38,rng);std::vector<int>permutation(64);std::iota(permutation.begin(),permutation.end(),0);
  double start=elapsed_sec();auto stats=assign_windows(a,6,38,comp.edge,comp.polarity,permutation,1e9,100000,25000,0);seconds[mode]+=(elapsed_sec()-start)/2;
  u64 hash=771130231;auto add=[&](u64 x){hash^=x+0x9e3779b97f4a7c15ULL+(hash<<6)+(hash>>2);};
  for(auto x:a)add(x);for(auto[a,b]:comp.edge)add(6*a+b);for(int x:comp.polarity)add(x);for(int x:permutation)add(x);
  if(!repeat&&!step)expected=hash;else assert(hash==expected);
 }
 std::cout<<std::setprecision(12)<<"[";for(int mode=0;mode<4;mode++)std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"bits\":"<<bits[mode]<<",\"seconds\":"<<seconds[mode]<<"}";std::cout<<"]\n";
}
