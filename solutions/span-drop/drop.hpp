// Changing one generic window into a handle preserves every old pair's
// compatibility. Keep the existing assignment, and create just one new column.
struct DropCandidate {
 std::unique_ptr<Design> d;
 Comparator comp;
 int window=-1,position=-1,moved=0;
 double model=1e100,merit=1e100;
};
u64 exchange_bits(u64 value,int a,int b){
 if(((value>>a)^(value>>b))&1)value^=(1ULL<<a)|(1ULL<<b);
 return value;
}
void complete_prices(Design&d,const Comparator&comp){
 for(int a=0;a<P;a++)for(int b=a+1;b<P;b++)if(comp.compatible(d.A[a],d.A[b])){
  d.ok[a][b]=d.ok[b][a]=1;d.partners[a].push_back(b);d.partners[b].push_back(a);
  auto r=comp.closure(d.A[a],d.A[a]^d.A[b]);u64 key=0;
  for(int z=0;z<6;z++)key|=u64(r[z])<<(8*z);
  d.gcost[a][b]=d.gcost[b][a]=PosetSums::get().both_of(key)/1440.;
 }
 d.refresh_reset();
}
std::vector<DropCandidate> drop_candidates(const Design&old,const Comparator&oldcomp,int shortlist=12){
 std::vector<DropCandidate> best;int G=old.G,H=old.H;
 for(int window=0;window<G;window++){
  if(std::count(oldcomp.edge.begin(),oldcomp.edge.end(),oldcomp.edge[window])<2)continue;
  Comparator comp;comp.M=6;comp.G=G-1;comp.edge=oldcomp.edge;comp.polarity=oldcomp.polarity;
  std::swap(comp.edge[window],comp.edge.back());std::swap(comp.polarity[window],comp.polarity.back());
  comp.edge.pop_back();comp.polarity.pop_back();comp.rebuild();assert(comp.complete);
  auto a=old.A;for(auto&v:a)v=exchange_bits(v,window,G-1);
  std::vector<double> prices(old.U);
  for(int x=0;x<old.U;x++)if(old.unit[x].b>=0){
   auto u=old.unit[x];assert(comp.compatible(a[u.a],a[u.b]));
   auto r=comp.closure(a[u.a],a[u.a]^a[u.b]);u64 key=0;
   for(int z=0;z<6;z++)key|=u64(r[z])<<(8*z);
   prices[x]=PosetSums::get().both_of(key)/1440.;
  }
  for(int pos=0;pos<=H;pos++){
   auto d=std::make_unique<Design>(a,6,G-1);d->handle=old.handle;d->handle.insert(d->handle.begin()+pos,G-1);
   for(int u=0;u<P;u++){d->hb[u]=0;for(int c=0;c<=H;c++)if(a[u]>>d->handle[c]&1)d->hb[u]|=1ULL<<c;}
   d->unit=old.unit;
   for(int x=0;x<d->U;x++){auto&u=d->unit[x];if(u.c>=pos)u.c++;if(u.b>=0)d->gcost[u.a][u.b]=d->gcost[u.b][u.a]=prices[x];}
   for(int c=0;c<H;c++)d->reset_targets[c+(c>=pos)]=old.reset_targets[c];
   d->rebuild();
   // The empty column is penalized; rank each removal with its temporary
   // one-color insertion, then check combinations without a linear assumption.
   std::array<std::vector<std::pair<double,int>>,2> ranked;
   auto transfer=[&](int x,int c){auto u=d->unit[x];d->update(u,-1);u.c=c;d->update(u,1);d->unit[x]=u;};
   auto removable=[&](int x){auto u=d->unit[x];int own=d->color(u,u.c);return (own?d->n1[u.c]:d->nc[u.c]-d->n1[u.c])>1;};
   for(int x=0;x<d->U;x++)if(d->valid(d->unit[x],pos)&&removable(x)){
    int c=d->unit[x].c,b=d->color(d->unit[x],pos);double before=d->cur;
    transfer(x,pos);ranked[b].push_back({d->cur,x});transfer(x,c);d->cur=before;
   }
   for(auto&v:ranked){std::sort(v.begin(),v.end());if(v.size()>12)v.resize(12);}
   double value=1e100;std::pair<int,int> choice{-1,-1};
   for(auto[ignored,x]:ranked[0]){
    int c=d->unit[x].c;double initial=d->cur;transfer(x,pos);
    for(auto[ignored2,y]:ranked[1])if(removable(y)){
     int e=d->unit[y].c;double before=d->cur;transfer(y,pos);
     if(d->cur<value)value=d->cur,choice={x,y};
     transfer(y,e);d->cur=before;
    }
    transfer(x,c);d->cur=initial;
   }
   if(choice.first<0)continue;
   transfer(choice.first,pos);transfer(choice.second,pos);int moved=2;
   while(true){
    int chosen=-1;double value=d->cur-1e-7;
    for(int x=0;x<d->U;x++)if(d->unit[x].c!=pos&&d->valid(d->unit[x],pos)&&removable(x)){
     int c=d->unit[x].c;double before=d->cur;transfer(x,pos);
     if(d->cur<value)value=d->cur,chosen=x;
     transfer(x,c);d->cur=before;
    }
    if(chosen<0)break;transfer(chosen,pos);moved++;
   }
   d->refresh_reset();
   for(int c=0;c<d->H;c++)assert(d->n1[c]>0&&d->n1[c]<d->nc[c]);
   for(auto u:d->unit)assert(d->valid(u,u.c));
   double model=d->cur/P;
   if(int(best.size())==shortlist&&model>=best.back().model)continue;
   DropCandidate item;item.d=std::move(d);item.comp=comp;item.window=window;item.position=pos;item.moved=moved;item.model=model;
   best.push_back(std::move(item));std::sort(best.begin(),best.end(),[](auto&a,auto&b){return a.model<b.model;});
   if(int(best.size())>shortlist)best.pop_back();
  }
 }
 for(auto&x:best){ProbabilityHead head(*x.d,2,true);x.merit=(x.d->cur-head.rebuild())/P;}
 return best;
}
