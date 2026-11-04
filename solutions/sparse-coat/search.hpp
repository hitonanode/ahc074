#define OVERCOAT_NO_MAIN
#include "probe.cpp"
struct Search {
 Solver&s;Comparator comp;XorShift rng{710000003};
 struct Pair{int a,b;u64 diff;double fixed;};std::vector<Pair> pairs;
 struct Result{double value=1e9;int special=0,novel=0,anchors=0,selected=0;};
 struct Entry{double cost;int pair,row,covered;};std::vector<Entry> ranked;std::vector<double>old,prices;std::vector<int>row,covered;
 std::array<u64,6>op{},black{};bool enabled=true;
 Search(Solver&v):s(v),comp(v.comparator){
  for(int a=0;a<P;a++)for(int b=a+1;b<P;b++){u64 d=(s.A[a]^s.A[b])&kActiveWindows;if(__builtin_popcountll(d)>26)continue;pairs.push_back({a,b,d,.5*__builtin_popcountll(d>>s.G)+.04*__builtin_popcountll(d)});}old.resize(pairs.size());prices.resize(pairs.size());row.resize(pairs.size());covered.resize(pairs.size());
 }
 double one(const std::array<unsigned,12>&r)const{u64 key=0;for(int x=0;x<6;x++){if(r[x]>>x&1)return -1;key|=u64(r[x])<<(8*x);}auto&t=PosetSums::get();return t.one[t.slot_of(key)]/720.;}
 Result evaluate(){
  comp.rebuild();op.fill(0);black.fill(0);for(int j=0;j<s.G;j++){auto[a,b]=comp.edge[j];op[a]|=1ULL<<j;op[b]|=1ULL<<j;black[comp.polarity[j]?a:b]|=1ULL<<j;}
  std::array<unsigned,256> matching{};int na=0;if(enabled)for(int b=0;b<P;b++)if(s.A[b]&kCapBit)for(int r=0;r<6;r++)if(!((s.A[b]^black[r])&op[r]))matching[b]|=1U<<r,na++;
  ranked.clear();
  for(int i=0;i<int(pairs.size());i++){
   auto&p=pairs[i];double a=one(comp.closure(s.A[p.a],p.diff));double price=a<0?-1:(a+one(comp.closure(s.A[p.b],p.diff)));old[i]=price;row[i]=covered[i]=-1;
   for(int b:{p.a,p.b})for(unsigned bits=matching[b];bits;bits&=bits-1){int r=__builtin_ctz(bits),other=b==p.a?p.b:p.a;u64 holes=p.diff&~op[r];auto ra=comp.closure(s.A[other],holes),rb=comp.closure(s.A[b],holes);double ca=one(ra);if(ca<0)continue;rb[r]=63U^(1U<<r);double cb=one(rb);assert(cb>=0);double v=ca+cb;if(price<0||v<price){price=v;row[i]=r;covered[i]=b;}}
   prices[i]=price<0?1e6:price+p.fixed;if(price>=0)ranked.push_back({prices[i],i,row[i],covered[i]});
  }
  std::sort(ranked.begin(),ranked.end(),[](auto a,auto b){return a.cost<b.cost||(a.cost==b.cost&&a.pair<b.pair);});std::array<bool,256>used{};std::vector<int> chosen;double sum=0;
  for(auto e:ranked){auto&p=pairs[e.pair];if(used[p.a]||used[p.b])continue;used[p.a]=used[p.b]=true;sum+=e.cost;chosen.push_back(e.pair);if(chosen.size()==71)break;}
  if(chosen.size()<71){std::array<std::vector<std::pair<int,int>>,256>n;for(auto e:ranked){auto&p=pairs[e.pair];n[p.a].emplace_back(p.b,e.pair);n[p.b].emplace_back(p.a,e.pair);}while(chosen.size()<71){double best=1e8;int bx=-1,bi=-1,bj=-1,bu=-1,bv=-1;for(int x=0;x<int(chosen.size());x++){auto&p=pairs[chosen[x]];for(auto[u,i]:n[p.a])if(!used[u])for(auto[v,j]:n[p.b])if(!used[v]&&u!=v){double d=prices[i]+prices[j]-prices[chosen[x]];if(d<best)best=d,bx=x,bi=i,bj=j,bu=u,bv=v;}}if(bx<0)break;used[bu]=used[bv]=true;sum+=best;chosen[bx]=bi;chosen.push_back(bj);}}
  Result r;r.value=sum/256+10*(71-int(chosen.size()));r.anchors=na;r.selected=chosen.size();for(int i:chosen)r.special+=row[i]>=0,r.novel+=old[i]<0;return r;
 }
};
