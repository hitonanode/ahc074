#include "saved.hpp"
#include <map>
#include <tuple>

struct Mixed {
 using Order=std::array<unsigned char,8>;
 struct Event {int own;u64 mask,color;int count;};
 struct Graph {std::vector<int>start,previous;std::vector<unsigned>visible;};
 struct Variant {
  int exclude=-1,n=0;bool strict=false;
  std::vector<Order>perm;
  std::vector<int>rank_map,next;
  std::vector<u64>shown;
  std::vector<double>bias;
  std::vector<int>best_return;
  Graph graph;
  int raw_rank(const Order&p)const{
   int rank=0;unsigned used=0;
   for(int i=0;i<n;i++){int x=p[i]-(exclude>=0&&p[i]>exclude);int smaller=__builtin_popcount(((1U<<x)-1)&~used);rank=rank*(n-i)+smaller;used|=1U<<x;}return rank;
  }
  int rank(const Order&p)const{return rank_map[raw_rank(p)];}
 };
 std::vector<u64>op,black;
 std::vector<Event>events;
 std::array<Variant,3>variant;
 std::array<std::vector<int>,2>removed;
 std::array<std::vector<std::vector<int>>,2>inserted;
 std::vector<std::vector<int>>goals,access_sources;
 std::vector<double>h;
 u64 mask;
 int iterations=0;double lower=0,upper=0,seconds=0,active=0,build_seconds=0; bool feasible=true;
 static constexpr double infinity=1e20;
 Mixed(std::vector<u64>o,std::vector<u64>b,std::vector<Event>e,u64 windows,bool strict):op(std::move(o)),black(std::move(b)),events(std::move(e)),mask(windows){
  auto start=std::chrono::steady_clock::now();
  for(int index=0;index<3;index++){
   auto&v=variant[index];v.exclude=index?index+5:-1;v.n=8-(index!=0);v.strict=strict;
   int fact=1;for(int i=2;i<=v.n;i++)fact*=i;v.rank_map.assign(fact,-1);
   Order order{};int n=0;for(int k=0;k<8;k++)if(k!=v.exclude)order[n++]=k;
   do{
    bool allowed=true;if(strict)for(int i=0;i<6;i++)if(order[i]>=6)allowed=false;
    if(allowed){v.rank_map[v.raw_rank(order)]=v.perm.size();v.perm.push_back(order);}
   }while(std::next_permutation(order.begin(),order.begin()+v.n));
   int states=v.perm.size();v.shown.resize(states);v.bias.resize(states);v.next.resize(size_t(states)*v.n*v.n);
   for(int s=0;s<states;s++){
    u64 covered=0;for(int i=0;i<v.n;i++){int k=v.perm[s][i];v.shown[s]|=black[k]&~covered;covered|=op[k];}
    for(int from=0;from<v.n;from++)for(int to=0;to<v.n;to++){
     Order p=v.perm[s];int k=p[from];if(from<to)for(int j=from;j<to;j++)p[j]=p[j+1];else for(int j=from;j>to;j--)p[j]=p[j-1];p[to]=k;
     v.next[(size_t(s)*v.n+from)*v.n+to]=v.rank(p);
    }
   }
   u64 open=mask;if(index)open&=~op[v.exclude];auto&g=v.graph;g.start.assign(states+1,0);g.visible.resize(states);
   for(int s=0;s<states;s++){
    u64 covered=0;unsigned vis=0;for(int i=0;i<v.n;i++){int k=v.perm[s][i];if(op[k]&open&~covered)vis|=1U<<i;covered|=op[k];}g.visible[s]=vis;
    for(unsigned bits=vis;bits;bits&=bits-1){int from=__builtin_ctz(bits);for(int to=0;to<v.n;to++)if(from!=to){int target=v.next[(size_t(s)*v.n+from)*v.n+to];if(target>=0)g.start[target+1]++;}}
   }
   for(int s=0;s<states;s++)g.start[s+1]+=g.start[s];g.previous.resize(g.start.back());auto cursor=g.start;
   for(int s=0;s<states;s++)for(unsigned bits=g.visible[s];bits;bits&=bits-1){int from=__builtin_ctz(bits);for(int to=0;to<v.n;to++)if(from!=to){int target=v.next[(size_t(s)*v.n+from)*v.n+to];if(target>=0)g.previous[cursor[target]++]=s;}}
  }
  auto&full=variant[0];int states=full.perm.size();h.assign(states,0);
  for(int k=0;k<2;k++){
   auto&v=variant[k+1];removed[k].resize(states);inserted[k].resize(v.perm.size());
   for(int s=0;s<states;s++){Order p{};int n=0;for(int i=0;i<8;i++)if(full.perm[s][i]!=k+6)p[n++]=full.perm[s][i];removed[k][s]=v.rank(p);assert(removed[k][s]>=0);}
   for(int s=0;s<int(v.perm.size());s++)for(int pos=0;pos<8;pos++){
    Order p{};for(int i=0,j=0;i<8;i++)p[i]=i==pos?k+6:v.perm[s][j++];int t=full.rank(p);if(t>=0)inserted[k][s].push_back(t);
   }
  }
  goals.resize(events.size());access_sources.resize(2);
  for(int e=0;e<int(events.size());e++){
   auto event=events[e];int index=event.own<0?0:event.own+1;const auto&v=variant[index];
   for(int s=0;s<int(v.perm.size());s++)if(!((v.shown[s]^event.color)&event.mask))goals[e].push_back(s);
   if(goals[e].empty())feasible=false;
  }
  for(int k=0;k<2;k++)for(int s=0;s<states;s++)for(int i=0;i<8;i++)if(full.perm[s][i]==k+6&&(full.graph.visible[s]>>i&1))access_sources[k].push_back(s);
  build_seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 }
 static std::vector<double> propagate(const Graph&g,const std::vector<double>&terminal,std::vector<int>sources,std::vector<int>*root=nullptr,const std::vector<int>*terminal_root=nullptr){
  const int n=terminal.size();std::vector<double>value(n,infinity);std::erase_if(sources,[&](int s){return terminal[s]>=infinity/2;});std::sort(sources.begin(),sources.end(),[&](int a,int b){return terminal[a]<terminal[b];});
  if(root){root->assign(n,-1);for(int s:sources)(*root)[s]=terminal_root?(*terminal_root)[s]:s;}
  for(int s:sources)value[s]=terminal[s];std::vector<int>q(n);std::vector<unsigned char>done(n);int qb=0,qe=0;size_t si=0;
  while(si<sources.size()||qb<qe){int s;if(qb<qe&&(si==sources.size()||value[q[qb]]<=terminal[sources[si]]))s=q[qb++];else{s=sources[si++];if(value[s]<terminal[s])continue;}if(done[s])continue;done[s]=1;double next=value[s]+1;
   for(int j=g.start[s];j<g.start[s+1];j++){int old=g.previous[j];if(value[old]>next){value[old]=next;if(root)(*root)[old]=(*root)[s];assert(qe<n);q[qe++]=old;}}
  }return value;
 }
 void biases(){
  variant[0].bias=h;
  for(int k=0;k<2;k++){
   variant[k+1].best_return.resize(variant[k+1].perm.size());
   for(int s=0;s<int(variant[k+1].perm.size());s++){
    double best=infinity;int chosen=-1;for(int full:inserted[k][s])if(h[full]<best){best=h[full];chosen=full;}variant[k+1].bias[s]=best;variant[k+1].best_return[s]=chosen;
   }
  }
 }
 std::vector<double> cost(int e,std::vector<int>*root=nullptr){
  auto event=events[e];int index=event.own<0?0:event.own+1;auto&v=variant[index];std::vector<int>after_root;
  auto value=propagate(v.graph,v.bias,goals[e],root?(index?&after_root:root):nullptr,index?&v.best_return:nullptr);if(index==0)return value;
  int k=event.own;std::vector<double>terminal(h.size(),infinity);std::vector<int>terminal_root;if(root)terminal_root.resize(h.size(),-1);
  for(int s:access_sources[k]){terminal[s]=value[removed[k][s]];if(root)terminal_root[s]=after_root[removed[k][s]];}
  return propagate(variant[0].graph,terminal,access_sources[k],root,root?&terminal_root:nullptr);
 }
 std::vector<double> stationary(){
  biases();std::vector<std::vector<int>>policy(events.size());int requests=0;
  for(int e=0;e<int(events.size());e++){cost(e,&policy[e]);requests+=events[e].count;}
  std::vector<double>pi(h.size(),1./h.size()),next(h.size());
  for(int it=0;it<500;it++){
   std::fill(next.begin(),next.end(),0);
   for(int e=0;e<int(events.size());e++){double probability=double(events[e].count)/requests;for(int s=0;s<int(h.size());s++){assert(policy[e][s]>=0);next[policy[e][s]]+=probability*pi[s];}}
   double delta=0;for(int s=0;s<int(h.size());s++){delta+=std::abs(pi[s]-next[s]);pi[s]=.5*(pi[s]+next[s]);}if(delta<1e-9)break;
  }
  double value=0;for(int e=0;e<int(events.size());e++){auto v=cost(e);for(int s=0;s<int(h.size());s++)value+=double(events[e].count)/P*pi[s]*(v[s]-h[s]);}
  assert(value>=lower-2e-5&&value<=upper+2e-5);return pi;
 }
 double price(u64 required,u64 color,const std::vector<double>&pi){
  std::vector<int>source;for(int s=0;s<int(h.size());s++)if(!((variant[0].shown[s]^color)&required))source.push_back(s);
  if(source.empty())return infinity;auto v=propagate(variant[0].graph,h,std::move(source));
  double value=0;for(int s=0;s<int(h.size());s++)value+=pi[s]*(v[s]-h[s]);return value;
 }
 void solve(int limit=100,double tolerance=1e-5,double cutoff=infinity){
  auto start=std::chrono::steady_clock::now();int requests=0;for(auto e:events)requests+=e.count;active=double(requests)/P;
  for(int it=0;it<limit;it++){
   biases();std::vector<double>next(h.size());for(int e=0;e<int(events.size());e++){auto value=cost(e);double p=double(events[e].count)/requests;for(int s=0;s<int(h.size());s++)next[s]+=p*value[s];}
   double lo=infinity,hi=-infinity,mean=0;for(int s=0;s<int(h.size());s++){lo=std::min(lo,next[s]-h[s]);hi=std::max(hi,next[s]-h[s]);mean+=next[s];}mean/=h.size();lower=lo*active;upper=hi*active;iterations=it+1;
   for(int s=0;s<int(h.size());s++)h[s]=.4*h[s]+.6*(next[s]-mean);
   if(false)std::cerr<<"iteration "<<it<<" lower "<<lower<<" upper "<<upper<<" seconds "<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<'\n';
   if(upper-lower<tolerance||lower>=cutoff)break;
  }
  seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 }
};
