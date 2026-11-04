#include <algorithm>
#include <array>
#include <bit>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <unordered_map>
#include <vector>
#ifndef CLOCK_SCALE
#define CLOCK_SCALE 1.0
#endif
using U=std::uint64_t;
using Rows=std::array<unsigned,20>;
struct Problem{
 int M,G;U gm;bool complete=true;std::array<U,256>A{};std::vector<std::pair<int,int>>edge;
 std::array<std::array<bool,256>,256>compatible{};
 std::vector<std::array<unsigned,20>>prefixes;std::vector<int>bottoms;
 explicit Problem(const char*path){
  std::ifstream in(path);in>>M>>G;gm=(1ULL<<G)-1;for(auto&a:A)in>>a;
  std::array<unsigned,20>adj{};
  for(int j=0;j<G;j++){int a,b,pol;in>>a>>b>>pol;adj[a]|=1U<<b;adj[b]|=1U<<a;if(!pol)std::swap(a,b);edge.emplace_back(a,b);}
  assert(in&&M<=11);
  for(int a=0;a<M;a++)complete&=(adj[a]|(1U<<a))==((1U<<M)-1);
  for(int a=0;a<256;a++)for(int b=a+1;b<256;b++){Rows r{};compatible[a][b]=compatible[b][a]=extend(r,A[a],(A[a]^A[b])&gm);}
  std::mt19937_64 rng(729871);std::array<int,20>order{};std::iota(order.begin(),order.begin()+M,0);
  for(int i=0;i<32;i++){std::shuffle(order.begin(),order.begin()+M,rng);std::array<unsigned,20>before{};unsigned seen=0;for(int j=0;j<M;j++){before[order[j]]=seen;seen|=1U<<order[j];}prefixes.push_back(before);bottoms.push_back(order[M-1]);}
 }
 bool extend(Rows&reach,U target,U holes)const{
  for(U z=holes;z;z&=z-1){int j=std::countr_zero(z);auto[a,b]=edge[j];if(!(target>>j&1))std::swap(a,b);
   if(reach[b]>>a&1)return false;if(reach[a]>>b&1)continue;unsigned next=reach[b]|(1U<<b);
   for(int x=0;x<M;x++)if(x==a||(reach[x]>>a&1))reach[x]|=next;
  }return true;
 }
 double lower_cost(const Rows&reach,int samples=32)const{
  double total=0;
  for(int sample=0;sample<samples;sample++){
   std::array<unsigned,20>conflict{};
   for(int x=0;x<M;x++)for(unsigned z=reach[x]&prefixes[sample][x];z;z&=z-1){int y=std::countr_zero(z);conflict[x]|=1U<<y;conflict[y]|=1U<<x;}
   std::array<unsigned char,2048>valid{};valid[0]=1;int kept=0;unsigned bb=1U<<bottoms[sample];
   for(unsigned mask=1;mask<(1U<<M);mask++){
    int a=std::countr_zero(mask);unsigned rest=mask&(mask-1);valid[mask]=valid[rest]&&!(rest&conflict[a]);
    if(!valid[mask])continue;int n=std::popcount(mask);if(n<=kept)continue;
    // For a complete comparison graph, this witness condition is exact.
    // For a sparse graph we omit visibility and retain a lower bound.
    bool legal=!complete||(mask&bb);
    if(!legal)for(int b=0;b<M;b++)if(!(mask>>b&1)&&b!=bottoms[sample]&&!(reach[b]&(mask|bb))){legal=true;break;}
    if(legal)kept=n;
   }
   total+=M-kept;
  }
  return total/samples;
 }
};
