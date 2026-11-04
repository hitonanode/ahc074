#define FRONT_NO_MAIN
#include "exact.cpp"
#include <queue>
#include <cassert>

// Independent heap-based shortest paths, building the reverse graph directly
// from all legal visible moves rather than using Evaluator's CSR structure.
std::vector<float> shortest(const Exact&e,const Design&d,const std::vector<int>&sources,
                            const std::vector<float>&terminal,int fixed=-1){
 const auto&m=e.M;std::vector<std::vector<int>>reverse(m.S);
 for(int s=0;s<m.S;s++){
  if(fixed>=0&&m.perm[size_t(s)*m.K]!=fixed)continue;
  u64 covered=0;
  for(int pos=0;pos<m.K;pos++){
   int k=m.perm[size_t(s)*m.K+pos];bool visible=(d.op[k]&~covered)!=0;covered|=d.op[k];
   if(!visible)continue;
   for(int depth=0;depth<m.K;depth++)if(depth!=pos){
    int next=m.succ[(size_t(s)*m.K+pos)*m.K+depth];
    if(fixed<0||m.perm[size_t(next)*m.K]==fixed)reverse[next].push_back(s);
   }
  }
 }
 std::vector<float>value(m.S,1e30f);
 std::priority_queue<std::pair<float,int>,std::vector<std::pair<float,int>>,std::greater<std::pair<float,int>>>heap;
 for(int s:sources)value[s]=terminal[s],heap.push({value[s],s});
 while(!heap.empty()){
  auto[c,s]=heap.top();heap.pop();if(c!=value[s])continue;
  for(int next:reverse[s])if(value[next]>c+1)value[next]=c+1,heap.push({c+1,next});
 }
 return value;
}
int main(){
 std::mt19937 rng(981723);Model m;m.build(2,6);int checked=0;
 for(int trial=0;trial<12;trial++){
  Design d;d.op.resize(6);d.bk.resize(6);
  for(int k=0;k<6;k++)d.op[k]=1+rng()%3,d.bk[k]=rng()%4&d.op[k];
  Exact e(m);for(int mask=1;mask<4;mask++)for(int color=0;color<4;color++)if(!(color&~mask))e.events.push_back({-1,mask,color,1});
  for(int k=0;k<6;k++)for(int color=0;color<4;color++)if(!((color^d.bk[k])&d.op[k]))e.events.push_back({k,3,color,1});
  e.prepare_actual(d);
  for(auto&x:e.h)x=float(int(rng()%100)-50)/13;
  for(int j=0;j<int(e.events.size());j++){
   if(e.goals[j].empty())continue;
   const auto q=e.events[j];auto terminal=e.h;std::vector<float>answer;
   if(q.paper<0)answer=shortest(e,d,e.goals[j],terminal);
   else{
    for(int s:e.goals[j])for(int depth=0;depth<m.K;depth++)terminal[s]=std::min(terminal[s],e.h[m.succ[size_t(s)*m.K*m.K+depth]]);
    auto after=shortest(e,d,e.goals[j],terminal,q.paper);std::vector<int>sources;
    for(int s=0;s<m.S;s++){
     u64 covered=0;int pos=0;for(;m.perm[size_t(s)*m.K+pos]!=q.paper;pos++)covered|=d.op[m.perm[size_t(s)*m.K+pos]];
     if(d.op[q.paper]&~covered){sources.push_back(s);terminal[s]=after[m.succ[(size_t(s)*m.K+pos)*m.K]];}
    }
    answer=shortest(e,d,sources,terminal);
   }
   // prepare_actual returns early on impossible events, so remove them first
   // before constructing the CSR required by the fast implementation.
   Exact f(m);f.events={q};f.prepare_actual(d);assert(!f.infeasible);f.h=e.h;f.event_cost(0);
   for(int s=0;s<m.S;s++){assert(std::abs(f.dist[s]-answer[s])<2e-6);checked++;}
  }
 }
 std::cout<<"verified state/event distances = "<<checked<<'\n';
}
