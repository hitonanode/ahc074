#include "design.hpp"
#include <fstream>
#include <iomanip>
struct General {
 int Q;std::array<u64,256>A{};std::array<bool,256>cap{};std::array<int,6>anchor{};
 std::array<std::array<int,6>,6> states{};std::vector<std::pair<int,int>> edges;
 std::array<std::vector<int>,63> allowed;std::array<int,63> code{},e0{},e1{},pol{};std::vector<int> eligible;
 std::mt19937_64 rng;u64 mask=0;double proxy=1e9;
 struct Pair {int a,b;u64 d;};std::vector<Pair> pairs;
 General(const char* input,int q,int seed):Q(q),rng(175174+seed){
  std::ifstream f(input);int n,k,p,r;f>>n>>k>>p>>r;std::string s;for(int u=0;u<256;u++){f>>s;cap[u]=s[63]=='1';for(int j=0;j<63;j++)if(s[j]=='1')A[u]|=1ULL<<j;}
  for(int a=0;a<256;a++)for(int b=a+1;b<256;b++){u64 d=A[a]^A[b];if(__builtin_popcountll(d)<=26)pairs.push_back({a,b,d});}
  for(int x=0;x<6;x++)for(int y=x+1;y<6;y++)edges.emplace_back(x,y);
 }
 void rebuild(){
  std::array<int,30> pattern{};
  for(int i=0;i<Q;i++){std::array<int,6> rank{};for(int j=0;j<6;j++)rank[states[i][j]]=j;for(int e=0;e<15;e++){auto[x,y]=edges[e];pattern[2*e+int(rank[x]<rank[y])]|=1<<i;}}
  eligible.clear();for(int j=0;j<63;j++){int bits=0;for(int i=0;i<Q;i++)bits|=((A[anchor[i]]>>j)&1)<<i;allowed[j].clear();for(int c=0;c<30;c++)if(pattern[c]==bits)allowed[j].push_back(c);if(!allowed[j].empty())eligible.push_back(j);}
 }
 void install_codes(){for(int j=0;j<63;j++){auto[x,y]=edges[code[j]/2];e0[j]=x;e1[j]=y;pol[j]=code[j]&1;}}
 bool initialize(int G){
  for(int attempt=0;attempt<100;attempt++){
   for(int i=0;i<Q;i++){do{anchor[i]=rng()%256;}while(!cap[anchor[i]]||std::find(anchor.begin(),anchor.begin()+i,anchor[i])!=anchor.begin()+i);std::iota(states[i].begin(),states[i].end(),0);if(i)std::shuffle(states[i].begin(),states[i].end(),rng);}
   rebuild();if(int(eligible.size())<G)continue;std::array<int,63> assigned;assigned.fill(-1);
   auto augment=[&](auto&&self,int edge,std::array<bool,63>&seen)->bool{for(int j:eligible)if(!seen[j]){int found=-1;for(int c:allowed[j])if(c/2==edge)found=c;if(found<0)continue;seen[j]=true;if(assigned[j]<0||self(self,assigned[j]/2,seen)){assigned[j]=found;return true;}}return false;};
   bool ok=true;for(int e=0;e<15;e++){std::array<bool,63>seen{};if(!augment(augment,e,seen)){ok=false;break;}}if(!ok)continue;mask=0;for(int j:eligible){code[j]=assigned[j]<0?allowed[j][rng()%allowed[j].size()]:assigned[j];if(assigned[j]>=0)mask|=1ULL<<j;}
   while(__builtin_popcountll(mask)<G)mask|=1ULL<<eligible[rng()%eligible.size()];install_codes();return true;
  }return false;
 }
 bool seed_saved(const char* file,int wanted,int G){
  std::ifstream f(file);std::string line;std::array<u64,7> op{},black{};
  for(int k=0;k<7;k++){f>>line;for(int j=0;j<63;j++){if(line[j]!='.')op[k]|=1ULL<<j;if(line[j]=='1')black[k]|=1ULL<<j;}}
  if(!f)return false;mask=0;for(int k=1;k<=6;k++)mask|=op[k];if(__builtin_popcountll(mask)!=G)return false;
  for(u64 z=mask;z;z&=z-1){int j=__builtin_ctzll(z),x=-1,y=-1;for(int k=0;k<6;k++)if(op[k+1]>>j&1){if(x<0)x=k;else y=k;}if(x<0||y<0)return false;int e=std::find(edges.begin(),edges.end(),std::make_pair(x,y))-edges.begin();code[j]=2*e+int(black[x+1]>>j&1);}
  Q=0;rebuild();install_codes();std::vector<std::array<int,6>> perms;std::array<int,6> perm{0,1,2,3,4,5};do{perms.push_back(perm);}while(std::next_permutation(perm.begin(),perm.end()));
  for(int next=0;next<wanted;next++){
   auto saved_anchor=anchor;auto saved_states=states;auto saved_code=code;
   struct Candidate{int distance,u,p;};std::vector<Candidate> candidates;
   for(int pi=0;pi<int(perms.size());pi++){std::array<int,6>rank{};for(int j=0;j<6;j++)rank[perms[pi][j]]=j;u64 display=0;for(u64 z=mask;z;z&=z-1){int j=__builtin_ctzll(z);if(int(rank[e0[j]]<rank[e1[j]])==pol[j])display|=1ULL<<j;}
    for(int u=0;u<256;u++)if(cap[u]&&std::find(anchor.begin(),anchor.begin()+Q,u)==anchor.begin()+Q)candidates.push_back({__builtin_popcountll((display^A[u])&mask),u,pi});
   }
   std::sort(candidates.begin(),candidates.end(),[](auto a,auto b){return std::tuple(a.distance,a.u,a.p)<std::tuple(b.distance,b.u,b.p);});
   double best=1e9;std::array<int,6>best_anchor{};std::array<std::array<int,6>,6>best_states{};std::array<int,63>best_code{};
   for(int ci=0;ci<std::min(256,int(candidates.size()));ci++){
    auto candidate=candidates[ci];anchor=saved_anchor;states=saved_states;anchor[next]=candidate.u;states[next]=perms[candidate.p];Q=next+1;rebuild();bool ok=true;for(u64 z=mask;z;z&=z-1)if(allowed[__builtin_ctzll(z)].empty())ok=false;if(!ok)continue;
    for(int trial=0;trial<3;trial++){
     code=saved_code;std::array<int,15>count{};
     for(u64 z=mask;z;z&=z-1){int j=__builtin_ctzll(z);if(std::find(allowed[j].begin(),allowed[j].end(),code[j])==allowed[j].end())code[j]=allowed[j][rng()%allowed[j].size()];count[code[j]/2]++;}
     for(int e=0;e<15;e++)if(!count[e]){std::vector<std::pair<int,int>>options;for(u64 z=mask;z;z&=z-1){int j=__builtin_ctzll(z);if(count[code[j]/2]<2)continue;for(int c:allowed[j])if(c/2==e)options.emplace_back(j,c);}if(options.empty()){ok=false;break;}auto[j,c]=options[rng()%options.size()];count[code[j]/2]--;code[j]=c;count[e]++;}
     if(!ok)break;install_codes();double value=evaluate();if(value<best){best=value;best_anchor=anchor;best_states=states;best_code=code;}
    }
   }
   if(best>=1e5)return false;anchor=best_anchor;states=best_states;code=best_code;Q=next+1;rebuild();install_codes();
  }
  return true;
 }
 double evaluate()const{
  unsigned coverage=0;for(u64 z=mask;z;z&=z-1)coverage|=1U<<(code[__builtin_ctzll(z)]/2);if(coverage!=32767)return 1e6;
  struct E{double cost;int a,b;};std::vector<E> ranked;std::array<bool,256>frozen{};for(int i=0;i<Q;i++)frozen[anchor[i]]=true;
  for(auto p:pairs){if(frozen[p.a]||frozen[p.b])continue;std::array<unsigned,6>r{};
   for(u64 z=p.d&mask;z;z&=z-1){int j=__builtin_ctzll(z),x=e0[j],y=e1[j];if(int(A[p.a]>>j&1)!=pol[j])std::swap(x,y);r[x]|=1U<<y;}
   for(int k=0;k<6;k++)for(int x=0;x<6;x++)if(r[x]>>k&1)r[x]|=r[k];bool ok=true;u64 key=0;for(int x=0;x<6;x++){ok&=!(r[x]>>x&1);key|=u64(r[x])<<(8*x);}if(!ok)continue;
   double cost=PosetSums::get().both_of(key)/720.+.65*__builtin_popcountll(p.d&~mask)+.04*__builtin_popcountll(p.d);ranked.push_back({cost,p.a,p.b});
  }
  std::sort(ranked.begin(),ranked.end(),[](auto a,auto b){return a.cost<b.cost;});std::array<bool,256>used{};int n=0,need=71-Q;double sum=0;for(auto e:ranked)if(!used[e.a]&&!used[e.b]){used[e.a]=used[e.b]=true;sum+=e.cost;if(++n==need)break;}return (sum+20*(need-n))/need;
 }
 void optimize(int G,int iterations){
  auto ba=anchor;auto bs=states;auto bc=code;u64 bm=mask;double current=evaluate(),best=current;
  for(int it=0;it<iterations;it++){
   auto olda=anchor;auto olds=states;auto oldc=code;u64 oldm=mask;int kind=rng()%100;if(kind>=80&&Q==0)continue;bool shape=kind>=80;
   if(kind<60){int j;do{j=eligible[rng()%eligible.size()];}while(!(mask>>j&1));code[j]=allowed[j][rng()%allowed[j].size()];}
   else if(kind<80){int a=eligible[rng()%eligible.size()],b=eligible[rng()%eligible.size()];if((((mask>>a)^(mask>>b))&1)==0)continue;mask^=(1ULL<<a)^(1ULL<<b);if(!(oldm>>a&1))code[a]=allowed[a][rng()%allowed[a].size()];else code[b]=allowed[b][rng()%allowed[b].size()];}
   else{
    int i=rng()%Q;if(kind<90){int u=rng()%256;if(!cap[u]||std::find(anchor.begin(),anchor.begin()+Q,u)!=anchor.begin()+Q)continue;anchor[i]=u;}
    else{if(i==0)continue;std::swap(states[i][rng()%6],states[i][rng()%6]);}
    rebuild();if(int(eligible.size())<G){anchor=olda;states=olds;rebuild();continue;}u64 possible=0;for(int j:eligible){possible|=1ULL<<j;if(std::find(allowed[j].begin(),allowed[j].end(),code[j])==allowed[j].end())code[j]=allowed[j][rng()%allowed[j].size()];}mask&=possible;while(__builtin_popcountll(mask)<G)mask|=1ULL<<eligible[rng()%eligible.size()];
   }
   install_codes();double value=evaluate(),temp=.25*std::pow(.015,double(it)/iterations);
   if(value<=current||std::generate_canonical<double,53>(rng)<std::exp((current-value)/temp))current=value;
   else{anchor=olda;states=olds;code=oldc;mask=oldm;if(shape)rebuild();install_codes();}
   if(current<best){best=current;ba=anchor;bs=states;bc=code;bm=mask;}
  }
  anchor=ba;states=bs;code=bc;mask=bm;rebuild();install_codes();proxy=best;
 }
 void design(int G,int iterations)const{
  std::vector<int> windows,products;for(int j=0;j<63;j++)if(mask>>j&1)windows.push_back(j);for(int j=0;j<63;j++)if(!(mask>>j&1))windows.push_back(j);
  for(int a=0;a<256;a++)if(std::find(anchor.begin(),anchor.begin()+Q,a)==anchor.begin()+Q)products.push_back(a);for(int i=0;i<Q;i++)products.push_back(anchor[i]);
  std::vector<u64> target(256);for(int a=0;a<256;a++)for(int j=0;j<63;j++)target[a]|=((A[products[a]]>>windows[j])&1)<<j;
  Comparator comp;comp.M=6;comp.G=G;for(int j=0;j<G;j++){comp.edge.emplace_back(e0[windows[j]],e1[windows[j]]);comp.polarity.push_back(pol[windows[j]]);}comp.rebuild();assert(comp.complete);
  Design d(target,6,G,256-Q);auto cost=[&](u64 a,u64 b){auto r=comp.closure(a,a^b);u64 key=0;for(int x=0;x<6;x++)key|=u64(r[x])<<(8*x);return PosetSums::get().both_of(key)/1440.;};
  if(!d.initialize([&](u64 a,u64 b){return comp.compatible(a,b);},cost,[]{return false;})){std::cout<<",\"failed\":true";return;}
  d.anneal(1e9,iterations);d.filler_climb(1e9,60000);double gc=0;
  for(int a=256-Q;a<256;a++){auto r=comp.closure(target[a],low_bits(G));u64 key=0;for(int x=0;x<6;x++){assert(!(r[x]>>x&1));key|=u64(r[x])<<(8*x);}auto&t=PosetSums::get();gc+=t.one[t.slot_of(key)]/720.;}
  double col=0,hole=0,pairg=0;for(int c=0;c<d.H;c++){col+=d.colcost(c);hole+=d.hcost(c);}for(auto u:d.unit)pairg+=d.gc(u);assert(std::abs(d.cur-col-hole-pairg)<1e-5);
  std::cout<<",\"design_cost\":"<<(d.cur+gc)/256<<",\"optimistic_cost\":"<<(d.cur+gc-2*Q)/256<<",\"columns\":"<<col/256<<",\"holes\":"<<hole/256<<",\"pair_generic\":"<<pairg/256<<",\"anchor_generic\":"<<gc/256;
 }};
int main(int argc,char**argv){if(argc<2)return 2;int Q=argc>2?std::stoi(argv[2]):4,G=argc>3?std::stoi(argv[3]):38,seed=argc>4?std::stoi(argv[4]):0,iters=argc>5?std::stoi(argv[5]):200000;
 auto start=std::chrono::steady_clock::now();General s(argv[1],Q,seed);if(!(argc>6?s.seed_saved(argv[6],Q,G):s.initialize(G))){std::cout<<"{\"failed\":true}\n";return 0;}s.optimize(G,iters);
 std::cout<<std::setprecision(12)<<"{\"Q\":"<<Q<<",\"G\":"<<G<<",\"eligible\":"<<s.eligible.size()<<",\"proxy\":"<<s.proxy<<",\"mask\":"<<s.mask<<",\"anchors\":[";for(int i=0;i<Q;i++)std::cout<<(i?",":"")<<s.anchor[i];std::cout<<"]";s.design(G,20000000);std::cout<<",\"elapsed\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<"}\n";return 0;}
