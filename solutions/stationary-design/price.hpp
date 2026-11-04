#include <map>

struct GenericPrice {
 struct Event {
  std::vector<int> goals;
  std::vector<unsigned char> distance;
  double uniform=0;
 };
 const Comparator& comp;
 int states=0;
 std::vector<Event> events;
 std::vector<std::array<int,4>> pairs; // a,b,event(a),event(b)
 std::array<std::array<int,P>,P> pair_index;
 std::array<std::array<float,P>,P> original;
 std::vector<double> h,stationary;
 double seconds=0,lower=0,upper=0,stationary_cost=0,spread=0;
 int iterations=0;
 GenericPrice(const Comparator& c,const Design& d):comp(c),states(c.perms.size()),original(d.gcost),h(states),stationary(states,1./states){
  assert(states==720);for(auto&row:pair_index)row.fill(-1);
  std::map<u64,int> cache;
  auto add=[&](int a,int b){
   auto reach=comp.closure(d.A[a],d.A[a]^d.A[b]);u64 key=0;for(int i=0;i<comp.M;i++)key|=u64(reach[i])<<(6*i);
   if(auto it=cache.find(key);it!=cache.end())return it->second;
   Event e;e.goals=comp.satisfying(d.A[a],d.A[a]^d.A[b]);assert(!e.goals.empty());
   int goals=e.goals.size();e.distance.resize(size_t(states)*goals);
   for(int s=0;s<states;s++){int closest=100;for(int j=0;j<goals;j++){int v=comp.distance(s,e.goals[j]);e.distance[size_t(s)*goals+j]=v;closest=std::min(closest,v);}e.uniform+=double(closest)/states;}
   int index=events.size();events.push_back(std::move(e));cache[key]=index;return index;
  };
  for(int a=0;a<P;a++)for(int b=a+1;b<P;b++)if(d.ok[a][b]){
   int index=pairs.size();pair_index[a][b]=pair_index[b][a]=index;
   int first=add(a,b),second=add(b,a);pairs.push_back({a,b,first,second});
   assert(std::abs(.5*(events[first].uniform+events[second].uniform)-d.gcost[a][b])<1e-5);
  }
 }
 void transform(int id,const std::vector<double>&value,std::vector<double>&cost,std::vector<int>*policy=nullptr)const{
  const auto&e=events[id];int goals=e.goals.size();cost.resize(states);if(policy)policy->resize(states);
  std::vector<double>terminal(goals);for(int j=0;j<goals;j++)terminal[j]=value[e.goals[j]];
  for(int s=0;s<states;s++){
   const auto*row=&e.distance[size_t(s)*goals];double best=1e100;int target=0;
   for(int j=0;j<goals;j++){double x=row[j]+terminal[j];if(x<best){best=x;target=j;}}
   cost[s]=best;if(policy)(*policy)[s]=e.goals[target];
  }
 }
 void update(Design&d,double strength){
  if(strength==0)return;
  auto start=std::chrono::steady_clock::now();std::vector<int>counts(events.size());int active=0;
  for(auto u:d.unit)if(u.b>=0){int i=pair_index[u.a][u.b];assert(i>=0);counts[pairs[i][2]]++;counts[pairs[i][3]]++;active+=2;}
  std::vector<int>used;for(int e=0;e<int(events.size());e++)if(counts[e])used.push_back(e);
  std::vector<double>next(states),cost;
  for(int it=0;it<200;it++){
   std::fill(next.begin(),next.end(),0);
   for(int e:used){transform(e,h,cost);double p=double(counts[e])/active;for(int s=0;s<states;s++)next[s]+=p*cost[s];}
   double lo=1e100,hi=-1e100,mean=0;
   for(int s=0;s<states;s++){lo=std::min(lo,next[s]-h[s]);hi=std::max(hi,next[s]-h[s]);mean+=next[s];}mean/=states;
   for(int s=0;s<states;s++)h[s]=.4*h[s]+.6*(next[s]-mean);
   iterations=it+1;lower=lo*active/P;upper=hi*active/P;
   if(upper-lower<1e-6)break;
  }
  std::vector<std::vector<int>>policy(used.size());
  for(int i=0;i<int(used.size());i++)transform(used[i],h,cost,&policy[i]);
  for(int it=0;it<500;it++){
   std::fill(next.begin(),next.end(),0);
   for(int i=0;i<int(used.size());i++){double p=double(counts[used[i]])/active;for(int s=0;s<states;s++)next[policy[i][s]]+=p*stationary[s];}
   double delta=0;for(int s=0;s<states;s++){delta+=std::abs(next[s]-stationary[s]);stationary[s]=.5*(stationary[s]+next[s]);}
   if(delta<1e-10)break;
  }
  double mean_h=0;for(int s=0;s<states;s++)mean_h+=stationary[s]*h[s];
  std::vector<double>price(events.size());
  for(int e=0;e<int(events.size());e++){transform(e,h,cost);double p=-mean_h;for(int s=0;s<states;s++)p+=stationary[s]*cost[s];price[e]=p;}
  stationary_cost=0;for(int e:used)stationary_cost+=double(counts[e])/P*price[e];
  assert(stationary_cost>=lower-2e-6&&stationary_cost<=upper+2e-6);
  double square=0;for(auto p:pairs){int a=p[0],b=p[1];double fresh=.5*(price[p[2]]+price[p[3]]);d.gcost[a][b]=d.gcost[b][a]=original[a][b]+strength*(fresh-original[a][b]);square+=(fresh-original[a][b])*(fresh-original[a][b]);}
  spread=std::sqrt(square/std::max(size_t(1),pairs.size()));
  d.rebuild();seconds+=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 }
};
