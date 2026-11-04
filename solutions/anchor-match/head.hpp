struct HeadModel{
 Design&d;std::vector<std::vector<double>>q;std::vector<std::array<double,2>>prob;
 std::vector<u64>diff;std::vector<double>utility,beta;
 HeadModel(Design&design):d(design),q(P,std::vector<double>(d.H+1)),prob(d.H),diff(d.U),utility(d.U),beta(d.U){
  for(int c=0;c<d.H;c++){double n=d.hn[c][0]+d.hn[c][1],p=n?d.hn[c][1]/n:.5;prob[c]={1-p,p};}
  for(int t=0;t<P;t++)for(int c=0;c<d.H;c++)q[t][c+1]=q[t][c]+2*prob[c][(d.hb[t]>>c&1)^1];
  rebuild();
 }
 double donor(const Design::Unit&u)const{
  double sum=0;u64 dy=u.b>=0?d.hb[u.a]^d.hb[u.b]:0;
  for(int t=0;t<P;t++)sum+=Design::filler_gain(d.hb[t],d.unit[d.owner[t]].c,diff[d.owner[t]],d.hb[u.a],dy,u.c,q[t].data());
  return sum;
 }
 double target(int t,const Design::Unit&u)const{
  double sum=0;u64 dx=u.b>=0?d.hb[u.a]^d.hb[u.b]:0;
  for(int y=0;y<d.U;y++)if(beta[y]){auto v=d.unit[y];sum+=beta[y]*Design::filler_gain(d.hb[t],u.c,dx,d.hb[v.a],diff[y],v.c,q[t].data());}
  return sum;
 }
 double rebuild(){
  for(int x=0;x<d.U;x++){auto u=d.unit[x];diff[x]=u.b>=0?d.hb[u.a]^d.hb[u.b]:0;}
  for(int x=0;x<d.U;x++)utility[x]=donor(d.unit[x]);
  std::vector<std::array<int,2>>best(d.H,{-1,-1});
  for(int x=0;x<d.U;x++){auto u=d.unit[x];int b=d.color(u,u.c),&y=best[u.c][b];if(y<0||d.weight(u)>d.weight(d.unit[y])||(d.weight(u)==d.weight(d.unit[y])&&utility[x]>utility[y]))y=x;}
  std::fill(beta.begin(),beta.end(),0);double sum=0;
  for(int c=0;c<d.H;c++)for(int b=0;b<2;b++){int y=best[c][b];assert(y>=0);beta[y]=prob[c][b];sum+=prob[c][b]*utility[y];}
  return sum;
 }
};
MatchStats rematch_head(Design&d,int iterations,double weight){
 auto start=std::chrono::steady_clock::now();MatchStats stats;d.refresh_reset();HeadModel head(d);double initial=d.cur-weight*head.rebuild(),merit=initial;
 std::mt19937_64 rng(0x181ba71c83ULL);
 for(int it=0;it<iterations;it++){
  std::vector<int>anchor(d.U,-1),mobile(d.U),color(d.U);
  for(int x=0;x<d.U;x++){auto u=d.unit[x];color[x]=d.color(u,u.c);mobile[x]=u.a;if(u.b>=0){anchor[x]=u.b;if(rng()&1)std::swap(anchor[x],mobile[x]);}}
  std::vector<std::array<double,2>>gradient(d.H);
  for(int j=0;j<d.H;j++){
   double x=d.hn[j][0],y=d.hn[j][1],t=d.reset_targets[j],den=std::max(1.,x+y+t),k=4*Design::kHoleWeight,n=x*y+.5*t*std::min(x,y);
   gradient[j]={k*((y+.5*t*(x<=y))*den-n)/(den*den),k*((x+.5*t*(y<x))*den-n)/(den*den)};
  }
  std::vector<std::vector<double>>tail(P,std::vector<double>(d.H+1)),single_target(P,std::vector<double>(d.H)),single_donor(P,std::vector<double>(d.H,-1));
  for(int a=0;a<P;a++){
   for(int j=d.H-1;j>=0;j--)tail[a][j]=tail[a][j+1]+gradient[j][d.hb[a]>>j&1];
   for(int c=0;c<d.H;c++)single_target[a][c]=head.target(a,{a,-1,c});
  }
  std::vector<std::vector<double>>cost(d.U,std::vector<double>(d.U,1e9));
  for(int i=0;i<d.U;i++){
   int c=d.unit[i].c,a=anchor[i];
   for(int j=0;j<d.U;j++){
    int b=mobile[j];if(int(d.hb[b]>>c&1)!=color[i]||(a>=0&&!d.ok[a][b]))continue;
    double v=tail[b][c+1],profit=0;Design::Unit u{b,a,c};
    if(a>=0){
     v+=tail[a][c+1]+2*d.gcost[a][b];for(u64 z=(d.hb[a]^d.hb[b])&low_bits(c+1);z;z&=z-1){int k=__builtin_ctzll(z);v+=gradient[k][0]+gradient[k][1];}
     profit=head.target(a,u)+head.target(b,u);if(head.beta[i])profit+=head.beta[i]*head.donor(u);
    }else{
     profit=single_target[b][c];if(head.beta[i]){auto&value=single_donor[b][c];if(value<0)value=head.donor(u);profit+=head.beta[i]*value;}
    }
    cost[i][j]=v-weight*profit;
   }
   assert(cost[i][i]<1e8);
  }
  auto assigned=hungarian(cost);std::vector<bool>seen(d.U);std::vector<std::pair<double,std::vector<int>>>cycles;
  for(int i=0;i<d.U;i++)if(!seen[i]){std::vector<int>cycle;double gain=0;int x=i;do{assert(!seen[x]);seen[x]=true;cycle.push_back(x);gain+=cost[x][assigned[x]]-cost[x][x];x=assigned[x];}while(x!=i);if(cycle.size()>1)cycles.push_back({gain,cycle});}
  std::sort(cycles.begin(),cycles.end(),[](auto&a,auto&b){return a.first<b.first;});
  for(auto&[predicted,cycle]:cycles){
   std::vector<Design::Unit>old;for(int x:cycle){old.push_back(d.unit[x]);d.unit[x].a=mobile[assigned[x]];d.unit[x].b=anchor[x];assert(d.valid(d.unit[x],d.unit[x].c));}
   d.rebuild();double next=d.cur-weight*head.rebuild();
   if(next<merit-1e-7){merit=next;stats.accepted_cycles++;stats.changed+=cycle.size();}
   else{for(int z=0;z<int(cycle.size());z++)d.unit[cycle[z]]=old[z];d.rebuild();head.rebuild();}
  }
  stats.iterations++;
 }
 stats.decrease=(merit-initial)/P;stats.seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();return stats;
}
