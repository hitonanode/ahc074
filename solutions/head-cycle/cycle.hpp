MatchStats cycle_head(Design&d,int iterations,double weight=1){
 auto start=std::chrono::steady_clock::now();MatchStats stats;d.refresh_reset();HeadModel head(d);double initial=d.cur-weight*head.rebuild(),merit=initial;
 for(int it=0;it<iterations;it++){
  std::vector<std::array<double,2>>gradient(d.H);
  for(int j=0;j<d.H;j++){
   double x=d.hn[j][0],y=d.hn[j][1],t=d.reset_targets[j],den=std::max(1.,x+y+t),k=4*Design::kHoleWeight,n=x*y+.5*t*std::min(x,y);
   gradient[j]={k*((y+.5*t*(x<=y))*den-n)/(den*den),k*((x+.5*t*(y<x))*den-n)/(den*den)};
  }
  std::vector<std::vector<double>>target(d.U,std::vector<double>(d.H)),donor(d.U,std::vector<double>(d.H,-1)),holes(d.U,std::vector<double>(d.H));
  for(int j=0;j<d.U;j++)for(int c=0;c<d.H;c++)if(d.valid(d.unit[j],c)){
   auto u=d.unit[j];u.c=c;target[j][c]=head.target(u.a,u);if(u.b>=0)target[j][c]+=head.target(u.b,u);
   for(u64 bits=d.holes(u);bits;bits&=bits-1){int b=__builtin_ctzll(bits);holes[j][c]+=gradient[b][d.hb[u.a]>>b&1];if(u.b>=0)holes[j][c]+=gradient[b][d.hb[u.b]>>b&1];}
  }
  std::vector<std::vector<double>>cost(d.U,std::vector<double>(d.U,1e9));
  for(int i=0;i<d.U;i++)for(int j=0;j<d.U;j++){
   auto u=d.unit[j];int c=d.unit[i].c;
   if((u.b>=0)!=(d.unit[i].b>=0)||!d.valid(u,c)||d.color(u,c)!=d.color(d.unit[i],c))continue;u.c=c;
   double profit=target[j][c];if(head.beta[i]){auto&v=donor[j][c];if(v<0)v=head.donor(u);profit+=head.beta[i]*v;}
   cost[i][j]=holes[j][c]-weight*profit;
  }
  auto assigned=hungarian(cost);std::vector<bool>seen(d.U);std::vector<std::pair<double,std::vector<int>>>cycles;auto original=d.unit;
  for(int i=0;i<d.U;i++)if(!seen[i]){std::vector<int>cycle;double gain=0;int x=i;do{assert(!seen[x]);seen[x]=true;cycle.push_back(x);gain+=cost[x][assigned[x]]-cost[x][x];x=assigned[x];}while(x!=i);if(cycle.size()>1)cycles.push_back({gain,cycle});}
  std::sort(cycles.begin(),cycles.end(),[](auto&a,auto&b){return a.first<b.first;});
  for(auto&[predicted,cycle]:cycles){
   std::vector<Design::Unit>old;for(int x:cycle){old.push_back(d.unit[x]);d.unit[x]=original[assigned[x]];d.unit[x].c=original[x].c;assert(d.valid(d.unit[x],d.unit[x].c));}
   d.rebuild();double next=d.cur-weight*head.rebuild();
   if(next<merit-1e-7){merit=next;stats.accepted_cycles++;stats.changed+=cycle.size();}
   else{for(int z=0;z<int(cycle.size());z++)d.unit[cycle[z]]=old[z];d.rebuild();head.rebuild();}
  }
  stats.iterations++;
 }
 stats.decrease=(merit-initial)/P;stats.seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();return stats;
}
