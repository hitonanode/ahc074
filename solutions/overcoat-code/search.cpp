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
int main(int argc,char**argv){if(argc<3)return 2;int steps=argc>3?std::stoi(argv[3]):20000;bool enabled=argc>4?std::stoi(argv[4]):1;auto source=coat::load(argv[1],argv[2]);if(!source)return 3;auto q=std::make_unique<Search>(*source);q->enabled=enabled;auto start=std::chrono::steady_clock::now();auto cur=q->evaluate(),base=cur,best=cur;auto be=q->comp.edge;auto bp=q->comp.polarity;
 std::array<std::array<int,6>,6>count{};for(auto[a,b]:q->comp.edge)count[a][b]++;
 for(int t=0;t<steps;t++){
  double temp=.025*std::pow(.002,double(t)/steps);int j=q->rng.mod(source->G),kind=q->rng.mod(5);auto old=q->comp.edge[j];int pol=q->comp.polarity[j];auto next=old;int np=pol;
  if(t%8==0){
   auto saved=q->comp.polarity;int r=q->rng.mod(6);std::vector<std::pair<int,int>> targets;
   for(int b=0;b<P;b++)if(source->A[b]&kCapBit)targets.emplace_back(__builtin_popcountll((source->A[b]^q->black[r])&q->op[r]),b);
   std::sort(targets.begin(),targets.end());int b=targets[q->rng.mod(std::min(16,int(targets.size())))].second;
   for(int k=0;k<source->G;k++){auto[a,z]=q->comp.edge[k];if(a==r||z==r)q->comp.polarity[k]=int(source->A[b]>>k&1)^(z==r);}
   auto candidate=q->evaluate();if(candidate.value<cur.value||q->rng.real()<std::exp((cur.value-candidate.value)/temp))cur=candidate;else q->comp.polarity=std::move(saved);
   if(cur.value<best.value){best=cur;be=q->comp.edge;bp=q->comp.polarity;}continue;
  }
  if(kind==0)np^=1;
  else if(kind<=2){if(count[old.first][old.second]<=1)continue;int a=q->rng.mod(6),b=q->rng.mod(5);if(b>=a)b++;if(a>b)std::swap(a,b);next={a,b};np=q->rng.mod(2);}
  else{int b=q->rng.mod(P),r=q->rng.mod(6);if(!(source->A[b]&kCapBit))continue;if(old.first==r||old.second==r)np=int(source->A[b]>>j&1)^(old.second==r);else continue;}
  if(next==old&&np==pol)continue;q->comp.edge[j]=next;q->comp.polarity[j]=np;auto candidate=q->evaluate();
  if(candidate.value<cur.value||q->rng.real()<std::exp((cur.value-candidate.value)/temp)){count[old.first][old.second]--;count[next.first][next.second]++;cur=candidate;}else q->comp.edge[j]=old,q->comp.polarity[j]=pol;
  if(cur.value<best.value){best=cur;be=q->comp.edge;bp=q->comp.polarity;}
 }
 q->comp.edge=be;q->comp.polarity=bp;best=q->evaluate();std::cout<<std::setprecision(12)<<"{\"enabled\":"<<enabled<<",\"base\":"<<base.value<<",\"best\":"<<best.value<<",\"special\":"<<best.special<<",\"novel\":"<<best.novel<<",\"anchors\":"<<best.anchors<<",\"iterations\":"<<steps<<",\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"gates\":[";
 for(int j=0;j<source->G;j++)std::cout<<(j?",":"")<<"["<<be[j].first<<","<<be[j].second<<","<<bp[j]<<"]";std::cout<<"]}\n";
}
