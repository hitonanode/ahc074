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
 double solve_actual(int limit=500,double tol=1e-7){
  if(infeasible)return 1e9;
  int count=0;for(auto e:events)count+=e.count;active=double(count)/256;
  for(int it=0;it<limit;it++){
   Th.assign(M.S,0);for(int e=0;e<int(events.size());e++){event_cost(e);double p=double(events[e].count)/count;for(int s=0;s<M.S;s++)Th[s]+=p*dist[s];}
   double lo=1e100,hi=-1e100,mean=0;for(int s=0;s<M.S;s++){double d=Th[s]-h[s];lo=std::min(lo,d);hi=std::max(hi,d);mean+=Th[s];}mean/=M.S;
   g_lo=lo*active;g_hi=hi*active;for(int s=0;s<M.S;s++)h[s]=.4*h[s]+.6*(Th[s]-mean);iterations=it+1;
   if((hi-lo)*active<tol)break;
  }return (g_lo+g_hi)/2;
 }
};
#ifndef FRONT_NO_MAIN
int main(int argc,char**argv){if(argc<2)return 2;std::ifstream in(argv[1]);int K,P,N;in>>K>>P>>N;if(K>8||N>3||P!=256)return 3;Model model;model.build(N,K);Design original;original.op.resize(K);original.bk.resize(K);std::vector<int>color(K),allowed(K),weights(K),id(K),col(K);
 for(int k=0;k<K;k++){in>>id[k]>>col[k]>>original.op[k]>>color[k]>>allowed[k];original.bk[k]=color[k]&original.op[k];}
 std::map<std::tuple<int,int,int>,int>counts;for(int u=0;u<P;u++){int k,m,c;in>>k>>m>>c;if(k>=0)weights[k]++,counts[{k,(1<<N)-1,c}]++;else if(m)counts[{k,m,c&m}]++;}if(!in)return 4;
 Exact e(model);for(auto[key,n]:counts){auto[k,m,c]=key;e.events.push_back({k,m,c,n});}e.prepare_actual(original);double baseline=e.solve_actual(1000,2e-7);double base_gap=e.g_hi-e.g_lo;
 Design current=original,best=original,chain=original;double bv=baseline,cv=baseline;int tested=0,valid=0;auto start=std::chrono::steady_clock::now();
 std::function<void(int)>visit=[&](int k){
  if(k<K){for(unsigned mask=1;mask<unsigned(1<<N);mask++)if(!(mask&~allowed[k])){
    bool canonical=true;for(int j=0;j<k;j++)if(color[j]==color[k]&&allowed[j]==allowed[k]&&weights[j]==weights[k]&&current.op[j]>mask)canonical=false;if(!canonical)continue;current.op[k]=mask;current.bk[k]=color[k]&mask;visit(k+1);
   }return;}
  tested++;e.prepare_actual(current);if(e.infeasible)return;valid++;double value=e.solve_actual(600,2e-7);if(e.g_hi-e.g_lo>2e-6)value=e.solve_actual(3000,2e-7);
  bool nested=true;for(auto a:current.op)for(auto b:current.op)if((a&b)!=a&&(a&b)!=b)nested=false;
  if(nested&&value<cv-1e-6)cv=value,chain=current;
  if(value<bv-1e-6){bv=value;best=current;std::cerr<<"best "<<tested<<" value "<<bv<<" gap "<<e.g_hi-e.g_lo<<" nested "<<nested<<'\n';}
 };
 visit(0);e.prepare_actual(best);std::fill(e.h.begin(),e.h.end(),0);bv=e.solve_actual(3000,2e-7);double best_gap=e.g_hi-e.g_lo;e.prepare_actual(chain);std::fill(e.h.begin(),e.h.end(),0);cv=e.solve_actual(3000,2e-7);
 std::cout<<std::setprecision(12)<<"{\"K\":"<<K<<",\"N\":"<<N<<",\"baseline\":"<<baseline<<",\"baseline_gap\":"<<base_gap<<",\"best\":"<<bv<<",\"best_gap\":"<<best_gap<<",\"chain\":"<<cv<<",\"chain_gap\":"<<e.g_hi-e.g_lo<<",\"difference\":"<<bv-baseline<<",\"difference_chain\":"<<bv-cv<<",\"active\":"<<e.active<<",\"tested\":"<<tested<<",\"valid\":"<<valid<<",\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"opaque\":[";
 for(int k=0;k<K;k++)std::cout<<(k?",":"")<<best.op[k];std::cout<<"],\"chain_opaque\":[";for(int k=0;k<K;k++)std::cout<<(k?",":"")<<chain.op[k];std::cout<<"]}\n";
}

#endif
