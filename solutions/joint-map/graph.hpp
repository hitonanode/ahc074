#include "matching.hpp"
struct JointMapGraph:JointMap {
 int graph_failures=0,assignment_failures=0;
 int refine_iterations=0;bool greedy_repair=true;
 bool assign(Design&d,const Design&previous,const std::vector<int>&matching){
  std::vector<std::array<double,2>>gradient(d.H);
  for(int c=0;c<d.H;c++){double n=previous.hn[c][0]+previous.hn[c][1];for(int b=0;b<2;b++)gradient[c][b]=n?4*d.kHoleWeight*std::pow(previous.hn[c][b^1]/n,2):d.kHoleWeight;}
  std::array<bool,P>placed{};
  for(int type=0;type<2;type++){
   std::vector<int>slots;std::vector<Design::Unit>rows;
   for(int x=0;x<d.U;x++)if((previous.unit[x].b>=0)==type){
    slots.push_back(x);auto u=previous.unit[x];
    if(type?matching[u.a]==u.b:matching[u.a]<0){rows.push_back(u);placed[u.a]=true;if(type)placed[u.b]=true;}
   }
   for(int a=0;a<P;a++)if(!placed[a]&&(matching[a]>=0)==type){
    int b=matching[a];if(b>=0&&placed[b])continue;rows.push_back({a,b,-1});placed[a]=true;if(b>=0)placed[b]=true;
   }
   int n=rows.size();if(n!=int(slots.size()))return false;
   std::vector<std::vector<double>>cost(n,std::vector<double>(n,1e8));
   for(int i=0;i<n;i++){
    auto u=rows[i];u64 diff=type?d.hb[u.a]^d.hb[u.b]:0;std::vector<double>suffix(d.H+1);
    for(int c=d.H-1;c>=0;c--)suffix[c]=suffix[c+1]+((diff>>c&1)?0:d.weight(u)*gradient[c][d.hb[u.a]>>c&1]);
    for(int j=0;j<n;j++){
     auto slot=previous.unit[slots[j]];int c=slot.c;
     if(d.valid(u,c)&&d.color(u,c)==previous.color(slot,c))cost[i][j]=suffix[c+1]+(c==u.c?0:1e-6);
    }
   }
   auto assignment=minimum_assignment(cost);
   for(int i=0;i<n;i++){
    if(cost[i][assignment[i]]>1e7)return false;
    rows[i].c=previous.unit[slots[assignment[i]]].c;d.unit[slots[i]]=rows[i];
   }
  }
  for(bool x:placed)assert(x);d.rebuild();return true;
 }

 void optimize(Design&design,Comparator&comparator,int iterations){
  auto start=std::chrono::steady_clock::now();before=design.cur/P;
  auto current=std::make_unique<Design>(design),best=std::make_unique<Design>(design);
  Comparator comp=comparator,best_comp=comp;double best_cost=design.cur;
  std::vector<std::pair<int,int>>edges,near;
  for(int a=0;a<6;a++)for(int b=a+1;b<6;b++)edges.emplace_back(a,b);
  for(int a=0;a<P;a++)for(int b=a+1;b<P;b++)if(__builtin_popcountll(design.A[a]^design.A[b])<=28)near.emplace_back(a,b);
  std::vector<unsigned char>seen(P*P);
  for(int it=0;it<iterations;it++){
   Comparator next=comp;int j=rng.below(next.G),kind=rng.below(4);
   if(kind==0)next.polarity[j]^=1;
   else if(kind==1){int k=rng.below(next.G);if(k==j)continue;std::swap(next.edge[j],next.edge[k]);if(rng.below(2))std::swap(next.polarity[j],next.polarity[k]);}
   else{int count=0;for(auto edge:next.edge)count+=edge==next.edge[j];if(count<2)continue;auto edge=edges[rng.below(edges.size())];if(edge==next.edge[j])continue;next.edge[j]=edge;if(rng.below(2))next.polarity[j]^=1;}
   next.rebuild();assert(next.complete);
   auto trial=std::make_unique<Design>(*current);std::fill(seen.begin(),seen.end(),0);
   CardinalMatching matching(P);std::vector<int>broken;
   int count=0;
   for(auto u:current->unit)if(u.b>=0){
    if(price(*trial,next,u.a,u.b,seen)){matching.match[u.a]=u.b;matching.match[u.b]=u.a;count++;}
    else broken.push_back(u.a),broken.push_back(u.b);
   }
   if(!broken.empty()){
    struct Edge{double cost;int a,b;};std::vector<Edge>ranked;
    for(auto[a,b]:near)if(price(*trial,next,a,b,seen)){
     u64 diff=trial->A[a]^trial->A[b];double cost=.5*__builtin_popcountll(diff&~low_bits(trial->G))+.04*__builtin_popcountll(diff)+2*trial->gcost[a][b];ranked.push_back({cost,a,b});
    }
    std::sort(ranked.begin(),ranked.end(),[](auto a,auto b){return a.cost<b.cost;});
    for(auto e:ranked){matching.g[e.a].push_back(e.b);matching.g[e.b].push_back(e.a);}
    // A broken pair need not keep either endpoint paired: a cheaper pair of
    // formerly single targets may replace it, leaving both endpoints single.
    if(greedy_repair)for(auto e:ranked)if(count<design.need&&matching.match[e.a]<0&&matching.match[e.b]<0){matching.match[e.a]=e.b;matching.match[e.b]=e.a;count++;}
    // Retained edges longer than the screening cutoff must also be present.
    for(int a=0;a<P;a++)if(matching.match[a]>a){int b=matching.match[a];if(std::find(matching.g[a].begin(),matching.g[a].end(),b)==matching.g[a].end()){matching.g[a].push_back(b);matching.g[b].push_back(a);}}
    int offset=rng.below(P);for(int t=0;t<P;t++)broken.push_back((offset+t)%P);
    for(int a:broken)if(count<design.need&&matching.match[a]<0)count+=matching.augment(a);
    if(count<design.need){failed++;graph_failures++;continue;}
    if(!assign(*trial,*current,matching.match)){failed++;assignment_failures++;continue;}
   }else trial->rebuild();
   if(refine_iterations&&!broken.empty()){
    for(auto&v:trial->partners)v.clear();
    for(int a=0;a<P;a++)for(int b=a+1;b<P;b++){
     bool valid=seen[a*P+b]&&trial->ok[a][b];trial->ok[a][b]=trial->ok[b][a]=valid;
     if(valid){trial->partners[a].push_back(b);trial->partners[b].push_back(a);}
    }
    trial->anneal(1e9,refine_iterations);
   }
   double temp=temperature*std::pow(.01,double(it)/std::max(1,iterations));
   if(trial->cur<current->cur||rng.real()<std::exp((current->cur-trial->cur)/temp)){
    accepted++;repaired+=broken.empty()?0:1;current=std::move(trial);comp=std::move(next);
    if(current->cur<best_cost){best_cost=current->cur;*best=*current;best_comp=comp;}
   }
  }
  for(int j=0;j<comp.G;j++)edge_changes+=best_comp.edge[j]!=comparator.edge[j]||best_comp.polarity[j]!=comparator.polarity[j];
  design=*best;comparator=best_comp;after=design.cur/P;
  seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 }
};
