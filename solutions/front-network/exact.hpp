#define main inherited_module_main
#include "module.hpp"
#undef main
#include <iomanip>
#include <functional>
#include <tuple>
struct Event {int paper,mask,color,count;};
struct Exact:Evaluator {
 std::vector<Event>events;std::vector<std::vector<int>>goals;double active=0;int iterations=0;
 Exact(const Model&m):Evaluator(m,1000){}
 void prepare_actual(const Design&d){
  rest.assign((1<<M.N)+M.K,{});goals.assign(events.size(),{});const int Q=1<<M.N;
  u64 all=0;for(auto o:d.op)all|=o;infeasible=all!=unsigned(Q-1);if(infeasible)return;
  for(int s=0;s<M.S;s++){
   const auto*p=&M.perm[s*M.K];u64 cov=0,display=0;unsigned visible=0;
   for(int i=0;i<M.K;i++){int k=p[i];u64 shown=d.op[k]&~cov;if(shown)visible|=1U<<i,rest[Q+k].push_back(s);display|=d.bk[k]&shown;cov|=d.op[k];}
   vis[s]=visible;tgt[s]=display;rest[display].push_back(s);
   for(int e=0;e<int(events.size());e++){auto q=events[e];if(q.paper<0){if(!((int(display)^q.color)&q.mask))goals[e].push_back(s);}else if(p[0]==q.paper&&int(display)==q.color)goals[e].push_back(s);}
  }
  for(auto&g:goals)infeasible+=g.empty();if(infeasible)return;
  pstart.assign(M.S+1,0);
  for(int y=0;y<M.S;y++){const auto*r=&M.succ[size_t(y)*M.K*M.K];for(unsigned v=vis[y];v;v&=v-1){int p=__builtin_ctz(v);for(int q=0;q<M.K;q++)if(p!=q)pstart[r[p*M.K+q]+1]++;}}
  for(int s=0;s<M.S;s++)pstart[s+1]+=pstart[s];pred.resize(pstart.back());fillp.assign(pstart.begin(),pstart.end()-1);
  for(int y=0;y<M.S;y++){const auto*r=&M.succ[size_t(y)*M.K*M.K];for(unsigned v=vis[y];v;v&=v-1){int p=__builtin_ctz(v);for(int q=0;q<M.K;q++)if(p!=q)pred[fillp[r[p*M.K+q]]++]=y;}}
 }
 void event_cost(int e){
  terminal=h;const int paper=events[e].paper;
  if(paper<0){propagate(goals[e]);return;}
  for(int s:goals[e])for(int depth=0;depth<M.K;depth++)terminal[s]=std::min(terminal[s],h[M.succ[size_t(s)*M.K*M.K+depth]]);
  propagate(goals[e],paper);const auto after=dist;
  for(int s:rest[(1<<M.N)+paper]){const auto*p=&M.perm[s*M.K];int pos=0;while(p[pos]!=paper)pos++;terminal[s]=after[M.succ[(size_t(s)*M.K+pos)*M.K]];}
  propagate(rest[(1<<M.N)+paper]);
 }
 double solve_actual(int limit=500,double tol=1e-7,double cutoff=1e100){
  if(infeasible)return 1e9;
  int count=0;for(auto e:events)count+=e.count;active=double(count)/256;
  for(int it=0;it<limit;it++){
   Th.assign(M.S,0);for(int e=0;e<int(events.size());e++){event_cost(e);double p=double(events[e].count)/count;for(int s=0;s<M.S;s++)Th[s]+=p*dist[s];}
   double lo=1e100,hi=-1e100,mean=0;for(int s=0;s<M.S;s++){double d=Th[s]-h[s];lo=std::min(lo,d);hi=std::max(hi,d);mean+=Th[s];}mean/=M.S;
   g_lo=lo*active;g_hi=hi*active;for(int s=0;s<M.S;s++)h[s]=.4*h[s]+.6*(Th[s]-mean);iterations=it+1;
   if((hi-lo)*active<tol||g_lo>=cutoff)break;
  }return (g_lo+g_hi)/2;
 }
};
