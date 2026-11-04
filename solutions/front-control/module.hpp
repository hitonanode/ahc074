#include <algorithm>
#include <array>
#include <cassert>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <numeric>
#include <vector>

struct FrontModel {
 static constexpr float infinity=1e25f;
 struct Event {int paper,mask,color,count;};
 struct Path {std::vector<float> value;std::vector<int> action;};
 struct Graph {
  std::vector<int> start,previous,action;
  std::vector<unsigned> visible;
 };
 struct Variant {
  int excluded=-1,n=0,states=0;
  std::vector<std::vector<int>> permutations;
  std::vector<int> next,shown;
  std::array<Graph,4> graph;
  std::array<std::vector<int>,9> goals;
  std::array<std::array<Path,9>,4> fix;
  std::vector<float> bias;
  int rank(const std::vector<int>&order)const{
   int rank=0;unsigned used=0;
   for(int i=0;i<n;i++){
    int x=order[i]-(excluded>=0&&order[i]>excluded);
    int smaller=__builtin_popcount(((1U<<x)-1)&~used);
    rank=rank*(n-i)+smaller;used|=1U<<x;
   }
   return rank;
  }
 };
 int count=0,iterations=0;
 std::vector<int> opaque,ink;
 std::vector<Event> events;
 std::vector<Variant> variants;
 // removed[k][s] is the smaller state after lifting paper k from full state s.
 std::vector<std::vector<int>> removed;
 std::vector<std::vector<std::vector<int>>> inserted;
 std::array<std::vector<std::array<Path,4>>,4> access;
 std::vector<float> h;
 double lower=0,upper=0,active=0,seconds=0;

 static int code(int mask,int color){return (mask&1?1+(color&1):0)+3*(mask&2?1+((color>>1)&1):0);}
 static int need_mask(int code){return (code%3?1:0)|(code/3?2:0);}
 static int need_color(int code){return (code%3==2?1:0)|(code/3==2?2:0);}
 FrontModel(std::vector<int>op,std::vector<int>black,std::vector<Event>requests):count(op.size()),opaque(std::move(op)),ink(std::move(black)),events(std::move(requests)){
  assert(count>=2&&count<=7);variants.resize(count+1);
  for(int index=0;index<=count;index++)build_variant(index);
  const int full=variants[0].states;h.assign(full,0);removed.assign(count,std::vector<int>(full));inserted.resize(count);
  for(int k=0;k<count;k++){
   auto&v=variants[k+1];inserted[k].resize(v.states);
   for(int s=0;s<full;s++){
    auto order=variants[0].permutations[s];order.erase(std::find(order.begin(),order.end(),k));removed[k][s]=v.rank(order);
   }
   for(int s=0;s<v.states;s++)for(int pos=0;pos<count;pos++){
    auto order=v.permutations[s];order.insert(order.begin()+pos,k);inserted[k][s].push_back(variants[0].rank(order));
   }
  }
  for(auto&v:access)v.resize(count);
 }
 void build_variant(int index){
  auto&v=variants[index];v.excluded=index-1;v.n=count-(index!=0);
  std::vector<int>order;for(int k=0;k<count;k++)if(k!=v.excluded)order.push_back(k);
  do{v.permutations.push_back(order);}while(std::next_permutation(order.begin(),order.end()));
  v.states=v.permutations.size();v.bias.resize(v.states);v.shown.resize(v.states);v.next.resize(size_t(v.states)*v.n*v.n);
  for(int s=0;s<v.states;s++){
   const auto&p=v.permutations[s];int covered=0,shown=0;
   for(int k:p){shown|=ink[k]&~covered;covered|=opaque[k];}v.shown[s]=shown;
   for(int c=0;c<9;c++)if(!((shown^need_color(c))&need_mask(c)))v.goals[c].push_back(s);
   for(int from=0;from<v.n;from++)for(int to=0;to<v.n;to++){
    auto next=p;int k=next[from];next.erase(next.begin()+from);next.insert(next.begin()+to,k);
    v.next[(size_t(s)*v.n+from)*v.n+to]=v.rank(next);
   }
  }
  for(int open=0;open<4;open++){
   auto&g=v.graph[open];g.start.assign(v.states+1,0);g.visible.resize(v.states);
   for(int s=0;s<v.states;s++){
    int covered=0;unsigned visible=0;
    for(int pos=0;pos<v.n;pos++){int k=v.permutations[s][pos];if(opaque[k]&open&~covered)visible|=1U<<pos;covered|=opaque[k];}g.visible[s]=visible;
    for(unsigned bits=visible;bits;bits&=bits-1){int pos=__builtin_ctz(bits);for(int to=0;to<v.n;to++)if(pos!=to)g.start[v.next[(size_t(s)*v.n+pos)*v.n+to]+1]++;}
   }
   for(int s=0;s<v.states;s++)g.start[s+1]+=g.start[s];g.previous.resize(g.start.back());g.action.resize(g.start.back());
   auto cursor=g.start;
   for(int s=0;s<v.states;s++)for(unsigned bits=g.visible[s];bits;bits&=bits-1){
    int pos=__builtin_ctz(bits);for(int to=0;to<v.n;to++)if(pos!=to){int target=v.next[(size_t(s)*v.n+pos)*v.n+to],at=cursor[target]++;g.previous[at]=s;g.action[at]=pos*v.n+to;}
   }
  }
 }
 // Sources have arbitrary bias, but every edge costs one. Merging sorted
 // sources with a FIFO of unit-edge discoveries is exact multi-source Dijkstra.
 static void propagate(const Graph&graph,const std::vector<float>&terminal,std::vector<int> sources,Path&result){
  const int n=terminal.size();result.value.assign(n,infinity);result.action.assign(n,-1);
  std::erase_if(sources,[&](int s){return terminal[s]>=infinity/2;});
  std::sort(sources.begin(),sources.end(),[&](int a,int b){return terminal[a]<terminal[b];});
  for(int s:sources)result.value[s]=terminal[s];
  std::vector<unsigned char>done(n);std::vector<int>queue(n);int begin=0,end=0;size_t si=0;
  while(si<sources.size()||begin<end){
   int s;if(begin<end&&(si==sources.size()||result.value[queue[begin]]<=terminal[sources[si]]))s=queue[begin++];
   else{s=sources[si++];if(result.value[s]<terminal[s])continue;}
   if(done[s])continue;done[s]=1;float next=result.value[s]+1;
   for(int edge=graph.start[s];edge<graph.start[s+1];edge++){
    int old=graph.previous[edge];if(result.value[old]>next){result.value[old]=next;result.action[old]=graph.action[edge];assert(end<n);queue[end++]=old;}
   }
  }
 }
 void biases(){
  variants[0].bias=h;
  for(int k=0;k<count;k++)for(int s=0;s<variants[k+1].states;s++){
   float value=infinity;for(int full:inserted[k][s])value=std::min(value,h[full]);variants[k+1].bias[s]=value;
  }
 }
 void fix_table(int variant,int open,int goal){
  auto&v=variants[variant];assert(!(need_mask(goal)&~open));propagate(v.graph[open],v.bias,v.goals[goal],v.fix[open][goal]);
 }
 void access_table(int open,int paper,int color){
  auto&full=variants[0];int after=open&~opaque[paper];auto&out=variants[paper+1];const auto&tail=out.fix[after][code(after,color)].value;
  std::vector<float>terminal(full.states,infinity);std::vector<int>sources;
  for(int s=0;s<full.states;s++){
   int position=std::find(full.permutations[s].begin(),full.permutations[s].end(),paper)-full.permutations[s].begin();
   if(full.graph[open].visible[s]>>position&1){terminal[s]=tail[removed[paper][s]];sources.push_back(s);}
  }
  propagate(full.graph[open],terminal,std::move(sources),access[open][paper][color]);
 }
 // `deadline` is a duration in scaled seconds. A partial value iteration still
 // yields legal paths; only the quality of the terminal bias is approximate.
 void solve(int limit=500,double tolerance=1e-6,double deadline=1e9){
  const auto start=std::chrono::steady_clock::now();int requests=0;for(auto e:events)requests+=e.count;active=requests/256.;
  std::array<int,9>external{};std::vector<std::array<int,4>>own(count);
  for(auto e:events)if(e.paper<0)external[code(e.mask,e.color)]+=e.count;else own[e.paper][e.color]+=e.count;
  for(int it=0;it<limit;it++){
   biases();std::vector<float>next(h.size());
   for(int c=0;c<9;c++)if(external[c]){
    fix_table(0,3,c);const auto&cost=variants[0].fix[3][c].value;float probability=float(external[c])/requests;
    for(int s=0;s<int(h.size());s++)next[s]+=probability*cost[s];
   }
   for(int k=0;k<count;k++)for(int c=0;c<4;c++)if(own[k][c]){
    int open=3&~opaque[k];fix_table(k+1,open,code(open,c));access_table(3,k,c);
    const auto&cost=access[3][k][c].value;float probability=float(own[k][c])/requests;
    for(int s=0;s<int(h.size());s++)next[s]+=probability*cost[s];
   }
   double lo=1e30,hi=-1e30,mean=0;
   for(int s=0;s<int(h.size());s++){double delta=next[s]-h[s];lo=std::min(lo,delta);hi=std::max(hi,delta);mean+=next[s];}mean/=h.size();
   lower=lo*active;upper=hi*active;iterations=it+1;
   for(int s=0;s<int(h.size());s++)h[s]=.4f*h[s]+.6f*(next[s]-mean);
   if(upper-lower<tolerance)break;
   if(CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()>=deadline)break;
  }
  biases();
  for(int v=0;v<=count;v++)for(int open=0;open<4;open++)for(int goal=0;goal<9;goal++)if(!(need_mask(goal)&~open))fix_table(v,open,goal);
  for(int open=0;open<4;open++)for(int k=0;k<count;k++)for(int color=0;color<4;color++)access_table(open,k,color);
  seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 }
};
