#include "../src/one_shot_planner.hpp"
#include <array>
#include <cassert>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
using namespace ahc074_one_shot;
Bits display(const std::vector<Paper>&p,const std::vector<int>&o) {
 Bits seen=0,view=0;for(int k:o){view|=p[k].black&~seen;seen|=p[k].opaque;}return view;
}
bool visible(const std::vector<Paper>&p,const std::vector<int>&o,int k) {
 Bits seen=0;for(int x:o){if(x==k)return p[x].opaque&~seen;seen|=p[x].opaque;}return false;
}
long long comparisons=0, plans=0;
void check(const std::vector<Paper>&p,const std::vector<int>&selected,int windows) {
 const int n=p.size(),r=selected.size();std::vector<int> initial(n);std::iota(initial.begin(),initial.end(),0);
 std::vector<std::vector<int>> final_orders;auto perm=selected;std::sort(perm.begin(),perm.end());
 do{final_orders.push_back(perm);}while(std::next_permutation(perm.begin(),perm.end()));
 std::vector<std::vector<bool>> feasible(final_orders.size(),std::vector<bool>(1<<windows));
 // Independent exhaustive enumeration: choose a currently visible paper,
 // try every insertion position, and never move a selected paper twice.
 auto enumerate=[&](auto&&self,std::vector<int>&o,unsigned done)->void{
  if(done==(1U<<r)-1){std::vector<int>f;for(int k:o)if(std::find(selected.begin(),selected.end(),k)!=selected.end())f.push_back(k);
   auto it=std::lower_bound(final_orders.begin(),final_orders.end(),f);feasible[it-final_orders.begin()][display(p,o)]=true;return;}
  for(int i=0;i<r;++i)if(!(done>>i&1)&&visible(p,o,selected[i])){
   auto rest=o;int k=selected[i];rest.erase(std::find(rest.begin(),rest.end(),k));
   for(int d=0;d<n;++d){auto next=rest;next.insert(next.begin()+d,k);self(self,next,done|(1U<<i));}
  }
 };
 enumerate(enumerate,initial,0);
 for(int i=0;i<int(final_orders.size());++i)for(int target=0;target<(1<<windows);++target){
  auto plan=solve(p,final_orders[i],target);++comparisons;
  if(bool(plan)!=feasible[i][target]){std::cerr<<"mismatch "<<comparisons<<'\n';std::exit(1);}
  if(plan){++plans;auto o=initial;for(auto m:plan->moves){assert(visible(p,o,m.original_index));o.erase(std::find(o.begin(),o.end(),m.original_index));o.insert(o.begin()+m.destination,m.original_index);}assert(display(p,o)==Bits(target));}
 }
}
int main(){
 for(int code=0;code<6561;++code){int z=code;std::vector<Paper>p(4);for(auto&x:p)for(int w=0;w<2;++w){int t=z%3;z/=3;if(t)x.opaque|=Bits(1)<<w;if(t==2)x.black|=Bits(1)<<w;}
  for(int skip=0;skip<4;++skip){std::vector<int>s;for(int k=0;k<4;++k)if(k!=skip)s.push_back(k);check(p,s,2);}
 }
 std::cout<<"{\"suite\":\"exhaustive_4papers_2windows_3selected\",\"comparisons\":"<<comparisons<<",\"plans_replayed\":"<<plans<<",\"mismatches\":0}\n";
 auto oldc=comparisons,oldp=plans;std::mt19937_64 rng(910772);
 for(int trial=0;trial<500;++trial){std::vector<Paper>p(5);for(auto&x:p)for(int w=0;w<3;++w){int t=rng()%3;if(t)x.opaque|=Bits(1)<<w;if(t==2)x.black|=Bits(1)<<w;}std::vector<int>s{0,1,2,3,4};s.erase(s.begin()+rng()%5);check(p,s,3);}
 std::cout<<"{\"suite\":\"random_5papers_3windows_4selected\",\"comparisons\":"<<comparisons-oldc<<",\"plans_replayed\":"<<plans-oldp<<",\"mismatches\":0}\n";
}
