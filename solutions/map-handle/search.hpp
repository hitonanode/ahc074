u64 exchange_bits(u64 x,int a,int b){if(((x>>a)^(x>>b))&1)x^=(1ULL<<a)|(1ULL<<b);return x;}
struct HandleMapCandidate{
 int j,c,flip;
 double model;
 std::array<float,K>prices{};
};
std::vector<HandleMapCandidate> enumerate_swaps(const Design&d,const Comparator&oldcomp){
 std::vector<HandleMapCandidate> candidates;
 for(int j=0;j<d.G;j++)for(int flip=0;flip<2;flip++){
  Comparator comp;comp.M=6;comp.G=d.G;comp.edge=oldcomp.edge;comp.polarity=oldcomp.polarity;comp.polarity[j]^=flip;comp.rebuild();
  for(int c=0;c<d.H;c++){
   int n1=0,p1=0,holes[2]={};bool valid=true;
   for(auto u:d.unit){
    int a=d.A[u.a]>>j&1,b=u.b<0?a:int(d.A[u.b]>>j&1);
    if(u.c==c){if(a!=b){valid=false;break;}n1+=a;p1+=a*(u.b>=0);}
    if(u.c<c||a!=b){holes[a]++;if(u.b>=0)holes[b]++;}
   }
   if(!valid||!n1||n1==d.nc[c])continue;
   HandleMapCandidate candidate{j,c,flip,d.cur};
   double generic=0;
   for(int x=0;x<d.U;x++){
    auto u=d.unit[x];if(u.b<0)continue;
    u64 a=exchange_bits(d.A[u.a],j,d.handle[c]),b=exchange_bits(d.A[u.b],j,d.handle[c]);
    auto reach=comp.closure(a,a^b);u64 key=0;
    for(int z=0;z<6;z++){if(reach[z]>>z&1){valid=false;break;}key|=u64(reach[z])<<(8*z);}
    if(!valid)break;
    float price=PosetSums::get().both_of(key)/1440.;candidate.prices[x]=price;generic+=2*(price-d.gcost[u.a][u.b]);
   }
   if(!valid)continue;
   double a=holes[0],b=holes[1],t=d.reset_targets[c];
   double hole=4*Design::kHoleWeight*(a*b+.5*t*std::min(a,b))/std::max(1.,a+b+t);
   candidate.model+=generic+hole-d.hcost(c)+Design::colcost_of(d.nc[c],d.nt[c],n1,p1)-d.colcost(c);
   candidates.push_back(candidate);
  }
 }
 std::sort(candidates.begin(),candidates.end(),[](auto&a,auto&b){return a.model<b.model;});return candidates;
}
Design apply_candidate(const Design&old,const HandleMapCandidate&candidate){
 Design d=old;
 for(int u=0;u<P;u++){
  d.A[u]=exchange_bits(old.A[u],candidate.j,d.handle[candidate.c]);
  d.hb[u]=(d.hb[u]&~(1ULL<<candidate.c))|((old.A[u]>>candidate.j&1)<<candidate.c);
 }
 for(int x=0;x<d.U;x++){auto u=d.unit[x];if(u.b>=0)d.gcost[u.a][u.b]=d.gcost[u.b][u.a]=candidate.prices[x];}
 d.rebuild();assert(std::abs(d.cur-candidate.model)<1e-4);return d;
}
void complete_prices(Design&d,const Comparator&comp){
 d.ok={};for(auto&v:d.partners)v.clear();
 for(int a=0;a<P;a++)for(int b=a+1;b<P;b++)if(comp.compatible(d.A[a],d.A[b])){
  d.ok[a][b]=d.ok[b][a]=1;d.partners[a].push_back(b);d.partners[b].push_back(a);
  auto r=comp.closure(d.A[a],d.A[a]^d.A[b]);u64 key=0;for(int z=0;z<6;z++)key|=u64(r[z])<<(8*z);
  d.gcost[a][b]=d.gcost[b][a]=PosetSums::get().both_of(key)/1440.;
 }
 d.refresh_reset();
}
struct SwapStats{int viable=0,accepted=0;double decrease=0,seconds=0;};
SwapStats optimize_swaps(Design&d,Comparator&comp,int mode,int rounds){
 SwapStats stats;double start=elapsed_sec(),before=d.cur;
 for(int round=0;round<rounds;round++){
  auto candidates=enumerate_swaps(d,comp);stats.viable+=candidates.size();
  ProbabilityHead base(d,2,true);double best=mode==1?d.cur:d.cur-base.rebuild();int choice=-1;
  int n=std::min(int(candidates.size()),mode==1?1:8);
  for(int i=0;i<n;i++){
   auto trial=apply_candidate(d,candidates[i]);ProbabilityHead head(trial,2,true);
   double merit=mode==1?trial.cur:trial.cur-head.rebuild();
   if(merit<best-1e-7){best=merit;choice=i;}
  }
  if(choice<0)break;
  auto selected=candidates[choice];d=apply_candidate(d,selected);comp.polarity[selected.j]^=selected.flip;comp.rebuild();stats.accepted++;
 }
 complete_prices(d,comp);stats.decrease=(d.cur-before)/P;stats.seconds=elapsed_sec()-start;return stats;
}
