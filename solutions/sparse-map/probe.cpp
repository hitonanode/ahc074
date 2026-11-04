#include "common.hpp"
#include "matching.hpp"
#include "prob.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 int iterations=argc>3?std::stoi(argv[3]):500000;double reference=0;
 std::cout<<std::setprecision(12)<<"[";
 for(int mode=0;mode<4;mode++){
  sparse_map_mode=mode;
  auto a=base->A;for(auto&x:a)x&=kActiveWindows;
  auto comp=base->comparator;comp.perms.clear();comp.next.clear();comp.below.clear();comp.dist.clear();comp.memo.clear();
  std::vector<std::pair<int,int>> allowed;for(int x=0;x<6;x++)for(int y=x+1;y<6;y++)if(sparse_allowed(x,y))allowed.push_back({x,y});
  XorShift init{0x913a715ULL};for(auto&e:comp.edge)if(!sparse_allowed(e.first,e.second))e=allowed[init.below(allowed.size())];
  std::vector<int> permutation(64);std::iota(permutation.begin(),permutation.end(),0);double start=elapsed_sec();
  auto stats=assign_windows(a,6,base->G,comp.edge,comp.polarity,permutation,1e9,iterations,iterations/5,0);
  comp.rebuild();double map_seconds=elapsed_sec()-start;
  comp.build_tables();for(auto x:comp.dist)assert(x<255);
  std::array<std::array<bool,6>,6> seen{};int edges=0;
  for(auto[x,y]:comp.edge)if(!seen[x][y])seen[x][y]=seen[y][x]=true,edges++;
  auto d=std::make_unique<Design>(a,6,base->G);
  double max_error=0;
  auto estimate=[&](u64 x,u64 y){
   double value=(comp.mean_moves(x,x^y)+comp.mean_moves(y,x^y))/2;
   if(comp.complete){auto r=comp.closure(x,x^y);u64 key=0;for(int k=0;k<6;k++)key|=u64(r[k])<<(8*k);max_error=std::max(max_error,std::abs(value-PosetSums::get().both_of(key)/1440.));}
   return value;
  };
  bool valid=d->initialize([&](u64 x,u64 y){return comp.compatible(x,y);},estimate,[]{return false;});assert(valid);assert(max_error<1e-6);
  d->anneal(1e9,20000000);d->filler_climb(1e9,65000);rematch_probability(*d,4,1,2,true,true);d->refresh_reset();
  double value=d->cur/P;if(!mode)reference=value;double generic=0;for(auto u:d->unit)generic+=d->gc(u);
  ProbabilityHead head(*d,2,true);double merit=(d->cur-head.rebuild())/P;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"model\":"<<value<<",\"difference\":"<<value-reference<<",\"merit\":"<<merit<<",\"generic\":"<<generic/P<<",\"edges\":"<<edges<<",\"gobj\":"<<stats.gobj_after<<",\"map_seconds\":"<<map_seconds<<",\"seconds\":"<<elapsed_sec()-start<<",\"design\":{\"A\":[";
  for(int u=0;u<P;u++)std::cout<<(u?",":"")<<(a[u]|(base->A[u]&kCapBit));
  std::cout<<"],\"handles\":[";for(int c=0;c<d->H;c++)std::cout<<(c?",":"")<<d->handle[c];
  std::cout<<"],\"units\":[";for(int k=0;k<d->U;k++){auto u=d->unit[k];std::cout<<(k?",":"")<<"["<<u.a<<","<<u.b<<","<<u.c<<"]";}
  std::cout<<"],\"edge\":[";for(int j=0;j<comp.G;j++)std::cout<<(j?",":"")<<"["<<comp.edge[j].first<<","<<comp.edge[j].second<<","<<comp.polarity[j]<<"]";
  std::cout<<"]}}"<<std::flush;
 }
 std::cout<<"]\n";
}
