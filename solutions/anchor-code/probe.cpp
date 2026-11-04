#include "design.hpp"
#include <fstream>
#include <iomanip>
struct AnchorSearch {
 std::array<u64,256>A{};std::array<bool,256>cap{};std::array<int,6> anchor{};std::array<int,64> e0{},e1{},pol{},eligible{};int eligible_count=0;
 std::mt19937_64 rng;u64 mask=0;double proxy=1e9;
 struct Pair {int a,b;u64 d;};std::vector<Pair> pairs;
 AnchorSearch(const char* input,int seed):rng(843215+seed){std::ifstream f(input);int n,k,p,r;f>>n>>k>>p>>r;std::string s;for(int u=0;u<256;u++){f>>s;cap[u]=s[63]=='1';for(int j=0;j<63;j++)if(s[j]=='1')A[u]|=1ULL<<j;}for(int a=0;a<256;a++)for(int b=a+1;b<256;b++){u64 d=A[a]^A[b];if(__builtin_popcountll(d)<=26)pairs.push_back({a,b,d});}}
 double shape(std::array<int,6> a,bool install=false){
  int count=0;std::array<int,15> cnt{};int index[6][6]{};int ne=0;for(int x=0;x<6;x++)for(int y=x+1;y<6;y++)index[x][y]=ne++;
  for(int j=0;j<63;j++){int x=-1,y=-1,changes=0;for(int t=0;t<6;t++)if(((A[a[t]]^A[a[(t+1)%6]])>>j)&1){if(x<0)x=t;else y=t;changes++;}if(changes!=2)continue;count++;cnt[index[x][y]]++;if(install){eligible[eligible_count++]=j;e0[j]=x;e1[j]=y;pol[j]=A[a[x]]>>j&1;}}
  double score=count;for(int n:cnt){if(!n)score-=30;score+=.15*std::min(n,3);}return score;
 }
 void select(int iterations){
  for(int t=0;t<6;t++){do{anchor[t]=rng()%256;}while(!cap[anchor[t]]||std::find(anchor.begin(),anchor.begin()+t,anchor[t])!=anchor.begin()+t);}
  auto best=anchor;double value=shape(anchor),bv=value;
  for(int it=0;it<iterations;it++){auto next=anchor;int x=rng()%6;if(rng()%5)next[x]=rng()%256;else std::swap(next[x],next[rng()%6]);if(!cap[next[x]])continue;auto copy=next;std::sort(copy.begin(),copy.end());if(std::adjacent_find(copy.begin(),copy.end())!=copy.end())continue;double score=shape(next),temp=2*std::pow(.01,double(it)/iterations);if(score>=value||std::generate_canonical<double,53>(rng)<std::exp((score-value)/temp)){anchor=next;value=score;}if(value>bv){bv=value;best=anchor;}}
  anchor=best;eligible_count=0;shape(anchor,true);
 }
 double evaluate(u64 chosen)const{
  unsigned edges=0;int index[6][6]{};int ne=0;for(int x=0;x<6;x++)for(int y=x+1;y<6;y++)index[x][y]=ne++;
  for(u64 z=chosen;z;z&=z-1){int j=__builtin_ctzll(z);edges|=1U<<index[e0[j]][e1[j]];}if(edges!=32767)return 1e6;
  struct E{double cost;int a,b;};std::vector<E> ranked;std::array<bool,256> frozen{};for(int a:anchor)frozen[a]=true;
  for(auto p:pairs){if(frozen[p.a]||frozen[p.b])continue;std::array<unsigned,6> r{};for(u64 z=p.d&chosen;z;z&=z-1){int j=__builtin_ctzll(z),x=e0[j],y=e1[j];if(int(A[p.a]>>j&1)!=pol[j])std::swap(x,y);r[x]|=1U<<y;}
   for(int k=0;k<6;k++)for(int x=0;x<6;x++)if(r[x]>>k&1)r[x]|=r[k];bool ok=true;u64 key=0;for(int x=0;x<6;x++){if(r[x]>>x&1)ok=false;key|=u64(r[x])<<(8*x);}if(!ok)continue;double fee=PosetSums::get().both_of(key)/720.+.65*__builtin_popcountll(p.d&~chosen)+.04*__builtin_popcountll(p.d);ranked.push_back({fee,p.a,p.b});
  }
  std::sort(ranked.begin(),ranked.end(),[](auto a,auto b){return a.cost<b.cost;});std::array<bool,256> used{};int n=0;double sum=0;for(auto e:ranked)if(!used[e.a]&&!used[e.b]){used[e.a]=used[e.b]=true;sum+=e.cost;if(++n==65)break;}return (sum+20*(65-n))/65;
 }
 bool choose_windows(int G,int iterations){if(eligible_count<G)return false;std::vector<int> all(eligible.begin(),eligible.begin()+eligible_count);std::shuffle(all.begin(),all.end(),rng);mask=0;for(int j=0;j<G;j++)mask|=1ULL<<all[j];double value=evaluate(mask),best=value;u64 bm=mask;
  for(int it=0;it<iterations;it++){int a=eligible[rng()%eligible_count],b=eligible[rng()%eligible_count];if(((mask>>a)^(mask>>b))%2==0)continue;u64 next=mask^(1ULL<<a)^(1ULL<<b);double nv=evaluate(next),temp=.12*std::pow(.02,double(it)/iterations);if(nv<=value||std::generate_canonical<double,53>(rng)<std::exp((value-nv)/temp)){mask=next;value=nv;}if(value<best){bm=mask;best=value;}}
  mask=bm;proxy=best;return best<1e5;
 }
 void joint(int G,int iterations){
  auto best_anchor=anchor;u64 best_mask=mask;double current=evaluate(mask),best=current;
  for(int it=0;it<iterations;it++){
   auto old_anchor=anchor;u64 old_mask=mask;bool changed=rng()%5==0;
   if(changed){int x=rng()%6;if(rng()%5){int u=rng()%256;if(!cap[u]||std::find(anchor.begin(),anchor.end(),u)!=anchor.end())continue;anchor[x]=u;}else std::swap(anchor[x],anchor[rng()%6]);eligible_count=0;shape(anchor,true);if(eligible_count<G){anchor=old_anchor;eligible_count=0;shape(anchor,true);continue;}
    u64 allowed=0;for(int j=0;j<eligible_count;j++)allowed|=1ULL<<eligible[j];mask&=allowed;while(__builtin_popcountll(mask)<G)mask|=1ULL<<eligible[rng()%eligible_count];
   }else{int a=eligible[rng()%eligible_count],b=eligible[rng()%eligible_count];if((((mask>>a)^(mask>>b))&1)==0)continue;mask^=(1ULL<<a)^(1ULL<<b);}
   double value=evaluate(mask),temp=.25*std::pow(.015,double(it)/iterations);
   if(value<=current||std::generate_canonical<double,53>(rng)<std::exp((current-value)/temp)){current=value;}
   else{mask=old_mask;anchor=old_anchor;if(changed){eligible_count=0;shape(anchor,true);}}
   if(current<best){best=current;best_anchor=anchor;best_mask=mask;}
  }
  anchor=best_anchor;mask=best_mask;proxy=best;eligible_count=0;shape(anchor,true);
 }
 void design(int G,int iterations)const{
  std::vector<int> windows,products;for(int j=0;j<63;j++)if(mask>>j&1)windows.push_back(j);for(int j=0;j<63;j++)if(!(mask>>j&1))windows.push_back(j);
  for(int a=0;a<256;a++)if(std::find(anchor.begin(),anchor.end(),a)==anchor.end())products.push_back(a);for(int a:anchor)products.push_back(a);
  std::vector<u64> target(256);for(int a=0;a<256;a++)for(int j=0;j<63;j++)target[a]|=((A[products[a]]>>windows[j])&1)<<j;
  Comparator comp;comp.M=6;comp.G=G;for(int j=0;j<G;j++){comp.edge.emplace_back(e0[windows[j]],e1[windows[j]]);comp.polarity.push_back(pol[windows[j]]);}comp.rebuild();assert(comp.complete);
  Design d(target,6,G,250);auto cost=[&](u64 a,u64 b){auto r=comp.closure(a,a^b);u64 key=0;for(int x=0;x<6;x++)key|=u64(r[x])<<(8*x);return PosetSums::get().both_of(key)/1440.;};
  if(!d.initialize([&](u64 a,u64 b){return comp.compatible(a,b);},cost,[]{return false;})){std::cout<<",\"failed\":true";return;}
  d.anneal(1e9,iterations);d.filler_climb(1e9,60000);double gc=0;
  for(int a=250;a<256;a++){auto r=comp.closure(target[a],low_bits(G));u64 key=0;for(int x=0;x<6;x++){assert(!(r[x]>>x&1));key|=u64(r[x])<<(8*x);}auto&t=PosetSums::get();gc+=t.one[t.slot_of(key)]/720.;}
  double col=0,hole=0,pairg=0;for(int c=0;c<d.H;c++){col+=d.colcost(c);hole+=d.hcost(c);}for(auto u:d.unit)pairg+=d.gc(u);assert(std::abs(d.cur-col-hole-pairg)<1e-5);
  std::cout<<",\"design_cost\":"<<(d.cur+gc)/256<<",\"optimistic_cost\":"<<(d.cur+gc-12)/256<<",\"columns\":"<<col/256<<",\"holes\":"<<hole/256<<",\"pair_generic\":"<<pairg/256<<",\"anchor_generic\":"<<gc/256;
 }
};
int main(int argc,char**argv){if(argc<2)return 2;int G=argc>2?std::stoi(argv[2]):38,seed=argc>3?std::stoi(argv[3]):0,iterations=argc>4?std::stoi(argv[4]):100000;
 auto start=std::chrono::steady_clock::now();AnchorSearch s(argv[1],seed);s.select(iterations);bool ok=s.choose_windows(G,3000);if(ok)s.joint(G,argc>5?std::stoi(argv[5]):100000);
 std::cout<<std::setprecision(12)<<"{\"G\":"<<G<<",\"eligible\":"<<s.eligible_count<<",\"proxy\":"<<s.proxy<<",\"mask\":"<<s.mask<<",\"anchors\":[";for(int i=0;i<6;i++)std::cout<<(i?",":"")<<s.anchor[i];std::cout<<"]";if(ok)s.design(G,20000000);else std::cout<<",\"failed\":true";
 std::cout<<",\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";return 0;}
