#include "saved.hpp"
#include <unordered_map>
int main(int argc,char**argv){
 if(argc<3)return 2;auto s=head::load(argv[1],argv[2]);if(!s)return 3;
 std::unordered_map<u64,int> targets;for(int u=0;u<P;u++)targets[s->A[u]&s->gmask]=u;
 std::array<std::array<int,K>,P> ways{};
 std::array<int,6> perm{0,1,2,3,4,5};
 do{
  std::array<u64,7> opq{},black{};
  for(int d=0;d<6;d++){black[d+1]=black[d]|(s->paper[perm[d]].black&~opq[d]);opq[d+1]=opq[d]|s->paper[perm[d]].opaque;}
  for(int x=7;x<K;x++)for(int d=0;d<=6;d++){
   const auto p=s->paper[x];u64 shown=black[d]|(p.black&~opq[d])|(black[6]&~(opq[d]|p.opaque));
   auto found=targets.find(shown&s->gmask);if(found==targets.end())continue;int u=found->second;
   if((s->A[u]^p.black)&p.opaque&s->hmask)continue;
   if((p.black&kCapBit)&&!(s->A[u]&kCapBit))continue;
   ways[u][x]++;
  }
 }while(std::next_permutation(perm.begin(),perm.end()));
 int alternatives=0,products=0;std::cout<<"{\"pairs\":[";
 for(int u=0;u<P;u++){bool any=false;assert(ways[u][s->ded[u]]);for(int x=7;x<K;x++)if(x!=s->ded[u]&&ways[u][x]){
  std::cout<<(alternatives?",":"")<<"["<<u<<","<<x<<","<<ways[u][x]<<","<<s->col_of[x]<<"]";alternatives++;any=true;
 }products+=any;}
 std::cout<<"],\"alternatives\":"<<alternatives<<",\"products\":"<<products<<"}\n";
}
