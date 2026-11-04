#define main latent_search_main
#include "search.cpp"
#undef main
int main(int argc,char**argv){
 if(argc<2)return 2;int tested=0;
 for(int M:{7,8}){
  Latent x(argv[1],M,38,35119);x.rebuild();
  for(int stage=0;stage<4;stage++){
   if(stage){x.choose_orders(.5);x.choose_mapping(8,.1);x.rebuild();}
   int n=0;std::vector<int>counts(x.ne);for(int j=0;j<63;j++)if(x.map.edge[j]>=0)n++,counts[x.map.edge[j]]++;
   assert(n==x.G);for(int c:counts)assert(c>0);
   for(int k=0;k<300;k++){
    int target=x.rng()%256;U holes=x.rng()&((1ULL<<63)-1)&x.generic_mask();
    int exact=64;for(U show:x.display)exact=std::min(exact,std::popcount((show^x.A[target])&holes));
    assert(exact==x.minimum_errors(target,holes));tested++;
   }
  }
 }
 std::cout<<tested<<" partial-target costs match permutation enumeration\n";
}
