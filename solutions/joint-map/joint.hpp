struct JointMap {
 XorShift rng{0xb816987ba18ULL};
 double temperature=.5,before=0,after=0,seconds=0;
 int accepted=0,failed=0,repaired=0,edge_changes=0;

 // Price just the pairs needed by this proposal. Reversed targets have reversed
 // relations, so the precomputed sum gives both request costs together.
 bool price(Design&d,const Comparator&c,int a,int b,std::vector<unsigned char>&seen){
  if(a>b)std::swap(a,b);int key=a*P+b;if(seen[key])return d.ok[a][b];seen[key]=1;
  auto relation=c.closure(d.A[a],d.A[a]^d.A[b]);bool valid=true;u64 code=0;
  for(int k=0;k<6;k++){if(relation[k]>>k&1)valid=false;code|=u64(relation[k])<<(8*k);}
  d.ok[a][b]=d.ok[b][a]=valid;
  d.gcost[a][b]=d.gcost[b][a]=valid?PosetSums::get().both_of(code)/1440.:1000.;
  return valid;
 }

 void optimize(Design&design,Comparator&comparator,int iterations){
  const auto start=std::chrono::steady_clock::now();before=design.cur/P;
  auto current=std::make_unique<Design>(design),best=std::make_unique<Design>(design);
  Comparator comp=comparator,best_comp=comp;double best_cost=design.cur;
  std::vector<std::pair<int,int>> edges;for(int a=0;a<6;a++)for(int b=a+1;b<6;b++)edges.emplace_back(a,b);
  std::vector<unsigned char>seen(P*P);
  for(int it=0;it<iterations;it++){
   Comparator next=comp;int j=rng.below(next.G),kind=rng.below(4);
   if(kind==0)next.polarity[j]^=1;
   else if(kind==1){int k=rng.below(next.G);if(k==j)continue;std::swap(next.edge[j],next.edge[k]);if(rng.below(2))std::swap(next.polarity[j],next.polarity[k]);}
   else{
    int count=0;for(auto edge:next.edge)count+=edge==next.edge[j];if(count<2)continue;
    auto edge=edges[rng.below(edges.size())];if(edge==next.edge[j])continue;next.edge[j]=edge;if(rng.below(2))next.polarity[j]^=1;
   }
   next.rebuild();assert(next.complete);
   auto trial=std::make_unique<Design>(*current);std::fill(seen.begin(),seen.end(),0);
   std::vector<int>broken;
   for(int x=0;x<trial->U;x++){auto u=trial->unit[x];if(u.b>=0&&!price(*trial,next,u.a,u.b,seen))broken.push_back(x);}
   trial->rebuild();bool possible=true;
   // Keep the old column of each pair; exchanging a single supplies the spare
   // endpoint without changing the number of sheets or leaving a target out.
   for(int x:broken){
    auto ox=trial->unit[x];double bv=1e100;int by=-1;Design::Unit bx,bz;
    for(int y=0;y<trial->U;y++)if(trial->unit[y].b<0){
     auto oy=trial->unit[y];
     for(int side=0;side<2;side++){
      Design::Unit nx{side?ox.b:ox.a,oy.a,ox.c},ny{side?ox.a:ox.b,-1,oy.c};
      if(!trial->valid(nx,nx.c)||!price(*trial,next,nx.a,nx.b,seen))continue;
      const double old=trial->cur;trial->update(ox,-1);trial->update(oy,-1);trial->update(nx,1);trial->update(ny,1);
      bool colors=true;for(int c:{ox.c,oy.c})if(!trial->n1[c]||trial->n1[c]==trial->nc[c])colors=false;
      if(colors&&trial->cur<bv){bv=trial->cur;by=y;bx=nx;bz=ny;}
      trial->update(nx,-1);trial->update(ny,-1);trial->update(ox,1);trial->update(oy,1);trial->cur=old;
     }
    }
    if(by<0){possible=false;break;}
    trial->update(trial->unit[x],-1);trial->update(trial->unit[by],-1);trial->unit[x]=bx;trial->unit[by]=bz;trial->update(bx,1);trial->update(bz,1);
   }
   if(!possible){failed++;continue;}
   trial->rebuild();
   const double temp=temperature*std::pow(.01,double(it)/std::max(1,iterations));
   if(trial->cur<current->cur||rng.real()<std::exp((current->cur-trial->cur)/temp)){
    accepted++;repaired+=broken.size();current=std::move(trial);comp=std::move(next);
    if(current->cur<best_cost){best_cost=current->cur;*best=*current;best_comp=comp;}
   }
  }
  for(int j=0;j<comp.G;j++)edge_changes+=best_comp.edge[j]!=comparator.edge[j]||best_comp.polarity[j]!=comparator.polarity[j];
  design=*best;comparator=best_comp;after=design.cur/P;
  seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 }
};
