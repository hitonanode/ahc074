u64 exchange_bits(u64 x,int a,int b){if(((x>>a)^(x>>b))&1)x^=(1ULL<<a)|(1ULL<<b);return x;}
double pair_price(const Comparator&comp,u64 a,u64 b){
 auto reach=comp.closure(a,a^b);u64 key=0;
 for(int z=0;z<6;z++){if(reach[z]>>z&1)return -1;key|=u64(reach[z])<<(8*z);}
 return float(PosetSums::get().both_of(key)/1440.);
}
void complete_prices(Design&d,const Comparator&comp){
 d.ok={};for(auto&v:d.partners)v.clear();
 for(int a=0;a<P;a++)for(int b=a+1;b<P;b++){
  double price=pair_price(comp,d.A[a],d.A[b]);if(price<0)continue;
  d.ok[a][b]=d.ok[b][a]=1;d.partners[a].push_back(b);d.partners[b].push_back(a);d.gcost[a][b]=d.gcost[b][a]=price;
 }
 d.refresh_reset();
}
struct RepairSwap{std::unique_ptr<Design>d;int j,flip,repairs;};
std::vector<RepairSwap> candidates(const Design&old,const Comparator&oldcomp,int limit,int&viable,int&repaired){
 std::vector<RepairSwap> best;
 for(int j=0;j<old.G;j++)for(int flip=0;flip<2;flip++){
  Comparator comp;comp.M=6;comp.G=old.G;comp.edge=oldcomp.edge;comp.polarity=oldcomp.polarity;comp.polarity[j]^=flip;comp.rebuild();
  for(int c=0;c<old.H;c++){
   std::array<float,K> prices{};std::vector<int> broken;
   for(int x=0;x<old.U;x++){
    auto u=old.unit[x];if(u.b<0)continue;
    u64 a=exchange_bits(old.A[u.a],j,old.handle[c]),b=exchange_bits(old.A[u.b],j,old.handle[c]);
    prices[x]=pair_price(comp,a,b);
    if(prices[x]<0||(u.c==c&&((a^b)>>old.handle[c]&1)))broken.push_back(x);
    if(int(broken.size())>limit)break;
   }
   if(int(broken.size())>limit)continue;viable++;
   auto d=std::make_unique<Design>(old);
   for(int u=0;u<P;u++){
    d->A[u]=exchange_bits(old.A[u],j,old.handle[c]);
    d->hb[u]=(old.hb[u]&~(1ULL<<c))|((old.A[u]>>j&1)<<c);
   }
   for(int x=0;x<d->U;x++){auto u=d->unit[x];if(u.b>=0)d->gcost[u.a][u.b]=d->gcost[u.b][u.a]=prices[x]<0?100:prices[x];}
   d->rebuild();bool valid=true;
   for(int x:broken){
    auto original=d->unit[x];double best_value=1e100;int choice=-1,which=-1;
    for(int y=0;y<d->U;y++)if(d->unit[y].b<0){
     auto single=d->unit[y];
     for(int flip_target=0;flip_target<2;flip_target++){
      int keep=flip_target?original.b:original.a,removed=flip_target?original.a:original.b;
      Design::Unit pair{keep,single.a,original.c},other{removed,-1,single.c};
      if(!d->valid(pair,pair.c))continue;
      double price=pair_price(comp,d->A[pair.a],d->A[pair.b]);if(price<0)continue;
      d->gcost[pair.a][pair.b]=d->gcost[pair.b][pair.a]=price;
      double before=d->cur;
      d->update(original,-1);d->update(single,-1);d->update(pair,1);d->update(other,1);
      if(d->cur<best_value){best_value=d->cur;choice=y;which=flip_target;}
      d->update(pair,-1);d->update(other,-1);d->update(original,1);d->update(single,1);d->cur=before;
     }
    }
    if(choice<0){valid=false;break;}
    auto single=d->unit[choice];int keep=which?original.b:original.a,removed=which?original.a:original.b;
    Design::Unit pair{keep,single.a,original.c},other{removed,-1,single.c};
    d->update(original,-1);d->update(single,-1);d->update(pair,1);d->update(other,1);
    d->unit[x]=pair;d->unit[choice]=other;
   }
   if(!valid||d->cur>1e4)continue;
   double before=d->cur;d->rebuild();assert(std::abs(before-d->cur)<1e-4);
   for(auto u:d->unit){assert(d->valid(u,u.c));if(u.b>=0)assert(comp.compatible(d->A[u.a],d->A[u.b]));}
   d->refresh_reset();
   repaired+=!broken.empty();best.push_back({std::move(d),j,flip,int(broken.size())});
   std::sort(best.begin(),best.end(),[](auto&a,auto&b){return a.d->cur<b.d->cur;});if(best.size()>12)best.resize(12);
  }
 }
 return best;
}
struct SwapStats{int viable=0,repaired=0,accepted=0;double decrease=0,seconds=0;};
SwapStats optimize_swaps(Design&d,Comparator&comp,int limit,bool use_head,int rounds){
 SwapStats stats;double start=elapsed_sec(),before=d.cur;
 for(int round=0;round<rounds;round++){
  auto list=candidates(d,comp,limit,stats.viable,stats.repaired);
  ProbabilityHead head(d,2,true);double best=d.cur-(use_head?head.rebuild():0);int choice=-1;
  for(int i=0;i<int(list.size());i++){
   ProbabilityHead next(*list[i].d,2,true);double merit=list[i].d->cur-(use_head?next.rebuild():0);
   if(merit<best-1e-7){best=merit;choice=i;}
  }
  if(choice<0)break;
  auto&selected=list[choice];d=std::move(*selected.d);comp.polarity[selected.j]^=selected.flip;comp.rebuild();stats.accepted++;
 }
 complete_prices(d,comp);stats.decrease=(d.cur-before)/P;stats.seconds=elapsed_sec()-start;return stats;
}
