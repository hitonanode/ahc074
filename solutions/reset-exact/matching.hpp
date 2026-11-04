struct MatchStats{int iterations=0,accepted_cycles=0,changed=0;double decrease=0,seconds=0;};
std::vector<int> hungarian(const std::vector<std::vector<double>>&cost){
 int n=cost.size();std::vector<double>u(n+1),v(n+1);std::vector<int>p(n+1),way(n+1);
 for(int i=1;i<=n;i++){
  p[0]=i;int j0=0;std::vector<double>minv(n+1,1e100);std::vector<bool>used(n+1);
  do{used[j0]=true;int i0=p[j0],j1=0;double delta=1e100;
   for(int j=1;j<=n;j++)if(!used[j]){double cur=cost[i0-1][j-1]-u[i0]-v[j];if(cur<minv[j])minv[j]=cur,way[j]=j0;if(minv[j]<delta)delta=minv[j],j1=j;}
   for(int j=0;j<=n;j++)if(used[j])u[p[j]]+=delta,v[j]-=delta;else minv[j]-=delta;j0=j1;
  }while(p[j0]);
  do{int j1=way[j0];p[j0]=p[j1];j0=j1;}while(j0);
 }
 std::vector<int>answer(n);for(int j=1;j<=n;j++)answer[p[j]-1]=j-1;return answer;
}
MatchStats rematch(Design&d,int iterations){
 auto start=std::chrono::steady_clock::now();MatchStats stats;d.refresh_reset();double initial=d.cur;
 std::mt19937_64 rng(0x181ba71c83ULL);
 for(int it=0;it<iterations;it++){
  std::vector<int>anchor(d.U,-1),mobile(d.U),color(d.U);
  for(int x=0;x<d.U;x++){auto u=d.unit[x];color[x]=d.color(u,u.c);mobile[x]=u.a;if(u.b>=0){anchor[x]=u.b;if(rng()&1)std::swap(anchor[x],mobile[x]);}}
  std::vector<std::array<double,2>>gradient(d.H);
  for(int j=0;j<d.H;j++){
   double x=d.hn[j][0],y=d.hn[j][1],t=d.reset_targets[j],den=std::max(1.,x+y+t),k=4*Design::kHoleWeight;
   double numerator=x*y+.5*t*std::min(x,y);
   double nx=y+.5*t*(x<=y),ny=x+.5*t*(y<x);
   gradient[j]={(k*(nx*den-numerator))/(den*den),(k*(ny*den-numerator))/(den*den)};
  }
  std::vector<std::vector<double>>tail(P,std::vector<double>(d.H+1));
  for(int a=0;a<P;a++)for(int j=d.H-1;j>=0;j--)tail[a][j]=tail[a][j+1]+gradient[j][d.hb[a]>>j&1];
  std::vector<std::vector<double>>cost(d.U,std::vector<double>(d.U,1e9));
  for(int i=0;i<d.U;i++){
   int c=d.unit[i].c,a=anchor[i];
   for(int j=0;j<d.U;j++){
    int b=mobile[j];if(int(d.hb[b]>>c&1)!=color[i]||(a>=0&&!d.ok[a][b]))continue;
    double v=tail[b][c+1];
    if(a>=0){v+=tail[a][c+1]+2*d.gcost[a][b];for(u64 z=(d.hb[a]^d.hb[b])&low_bits(c+1);z;z&=z-1){int k=__builtin_ctzll(z);v+=gradient[k][0]+gradient[k][1];}}
    cost[i][j]=v;
   }
   assert(cost[i][i]<1e8);
  }
  auto assigned=hungarian(cost);std::vector<bool>seen(d.U);
  std::vector<std::pair<double,std::vector<int>>>cycles;
  for(int i=0;i<d.U;i++)if(!seen[i]){
   std::vector<int>cycle;double gain=0;int x=i;
   do{assert(!seen[x]);seen[x]=true;cycle.push_back(x);gain+=cost[x][assigned[x]]-cost[x][x];x=assigned[x];}while(x!=i);
   if(cycle.size()>1)cycles.push_back({gain,cycle});
  }
  std::sort(cycles.begin(),cycles.end(),[](auto&a,auto&b){return a.first<b.first;});
  for(auto&[predicted,cycle]:cycles){
   std::vector<Design::Unit>old,next;double before=d.cur;
   for(int x:cycle){auto u=d.unit[x];old.push_back(u);u.a=mobile[assigned[x]];u.b=anchor[x];assert(d.valid(u,u.c));next.push_back(u);}
   for(auto u:old)d.update(u,-1);for(auto u:next)d.update(u,1);
   if(d.cur<before-1e-7){for(int z=0;z<int(cycle.size());z++)d.unit[cycle[z]]=next[z];stats.accepted_cycles++;stats.changed+=cycle.size();}
   else{for(auto u:next)d.update(u,-1);for(auto u:old)d.update(u,1);d.cur=before;}
  }
  double exact=d.cur;d.rebuild();assert(std::abs(exact-d.cur)<1e-5);stats.iterations++;
 }
 stats.decrease=(d.cur-initial)/P;stats.seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();return stats;
}
