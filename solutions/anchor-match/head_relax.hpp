MatchStats rematch_relax(Design&d,int iterations,double weight){
 auto start=std::chrono::steady_clock::now();MatchStats stats;d.refresh_reset();HeadModel head(d);double initial=d.cur-weight*head.rebuild(),merit=initial;
 std::mt19937_64 rng(0x181ba71c83ULL);
 for(int it=0;it<iterations;it++){
  std::vector<int>anchor(d.U,-1),mobile(d.U),color(d.U);
  for(int x=0;x<d.U;x++){auto u=d.unit[x];color[x]=d.color(u,u.c);mobile[x]=u.a;if(u.b>=0){anchor[x]=u.b;if(rng()&1)std::swap(anchor[x],mobile[x]);}}
  std::vector<bool>protected_color(d.U);
  for(int c=0;c<d.H;c++)for(int b=0;b<2;b++){
   bool pair=false;int chosen=-1;
   for(int x=0;x<d.U;x++)if(d.unit[x].c==c&&color[x]==b){
    if(anchor[x]>=0)pair=true;
    if(chosen<0||head.utility[x]>head.utility[chosen])chosen=x;
   }
   assert(chosen>=0);if(!pair)protected_color[chosen]=true;
  }
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
    int b=mobile[j];if(((a>=0||protected_color[i])&&int(d.hb[b]>>c&1)!=color[i])||(a>=0&&!d.ok[a][b]))continue;
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
