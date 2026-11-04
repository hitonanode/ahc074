#include "common.hpp"
constexpr int F=9;
using Features=std::array<double,F>;
Features features(const Solver&s,const std::array<int,K>&frequency){
 Features f{};std::array<std::array<int,2>,64>all_counts{},inside_counts{};
 for(int k=s.M+1;k<K;k++)all_counts[s.col_of[k]][frequency[k]-1]++;std::array<int,64>rank{};std::array<std::array<int,2>,64>first;for(auto&v:first)v={-1,-1};
 std::array<std::array<bool,2>,64>available{};std::array<bool,K>extra{};
 if(s.top_d>=0)extra[s.top_d]=true;for(auto x:s.fillers)extra[x.paper]=true;
 for(int k:s.order){int c=s.col_of[k];if(c<0)continue;int b=s.paper[k].black>>s.handle[c]&1;
  if(extra[k]){available[c][b]=true;continue;}
  inside_counts[c][frequency[k]-1]++;
  if(first[c][b]<0)first[c][b]=rank[c];
  f[0]+=frequency[k]*rank[c]/double(P);f[1]+=(s.adaptive_weights[k]-frequency[k])*rank[c]/double(P);rank[c]++;
 }
 std::array<std::array<double,2>,64>covered{};
 for(auto x:s.fillers){
  bool low=s.below_generic(x.paper);f[low?3:4]++;
  if(low){auto&v=s.stay_table[x.paper][x.lvl];f[5]+=.4-v.probability;
   for(int c=0;c<s.H;c++){int b=s.h_blk[x.paper]>>c&1;covered[c][b]=std::max(covered[c][b],v.cover[c]);}
  }
 }
 for(int c=0;c<s.H;c++)for(int b=0;b<2;b++){int fix=available[c][b]?0:first[c][b];if(fix<0)fix=rank[c];f[2]+=s.adaptive_holes[c][b]*fix;f[6]+=covered[c][b]*fix;}
 f[7]=s.fillers.size()*(s.fillers.size()-1)/2.;
 auto minimum=[](const std::array<int,2>&v){double a=v[0],b=v[1];return b*(b-1)+a*b+a*(a-1)/2;};
 for(int c=0;c<s.H;c++)f[8]+=(minimum(all_counts[c])-minimum(inside_counts[c]))/P;
 double expected=f[0]+f[1]+f[2]+.6*(f[3]+f[4])+.25*f[5]-.25*f[6];
 assert(std::abs(expected-s.adaptive_next_cost()-s.filler_charge())<1e-7);return f;
}
