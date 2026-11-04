struct TieHead{
 Design&d;std::vector<std::vector<double>>q;std::vector<std::array<double,2>>prob;
 std::vector<u64>diff;std::vector<double>utility,beta;
 static inline int bias_mode=0;
 double reset_strength;bool dynamic;
 TieHead(Design&design,double strength,bool update):d(design),q(P,std::vector<double>(d.H+1)),prob(d.H),diff(d.U),utility(d.U),beta(d.U),reset_strength(strength),dynamic(update){
  update_probability();
  rebuild();
 }
 void update_probability(){
  for(int c=0;c<d.H;c++){
   double x=d.hn[c][0],y=d.hn[c][1],t=reset_strength*d.nt[c],n=x+y+t,bias=y>x;
   if(bias_mode){
    double difference=y-x;
    if(bias_mode==2){std::array<int,2>highest{};for(auto u:d.unit)if(u.c==c)highest[d.color(u,c)]=std::max(highest[d.color(u,c)],d.weight(u));difference+=highest[1]-highest[0];}
    bias=difference>0?1:difference<0?0:.5;
   }
   double p=n?(y+t*bias)/n:.5;prob[c]={1-p,p};
  }
  for(int t=0;t<P;t++){q[t][0]=0;for(int c=0;c<d.H;c++)q[t][c+1]=q[t][c]+2*prob[c][(d.hb[t]>>c&1)^1];}
 }
 // Derivative of expected positive gain: 1 - P(other errors=0)
 // - 0.6 P(other errors=1). Prefix/suffix polynomials avoid dividing by
 // probabilities near zero or one.
 std::vector<double> probability_gradient()const{
  std::vector<double>gradient(d.H);std::vector<std::array<int,2>>selected(d.H,{-1,-1});
  for(int x=0;x<d.U;x++){auto u=d.unit[x];int b=d.color(u,u.c),&y=selected[u.c][b];if(y<0||d.weight(u)>d.weight(d.unit[y])||(d.weight(u)==d.weight(d.unit[y])&&utility[x]>utility[y]))y=x;}
  for(int c=0;c<d.H;c++)gradient[c]=utility[selected[c][1]]-utility[selected[c][0]];
  for(int y=0;y<d.U;y++)if(beta[y]){
   auto u=d.unit[y];int c=u.c;
   for(int t=0;t<P;t++){
    auto target=d.unit[d.owner[t]];if(c==target.c)continue;
    u64 range=low_bits(c+1)&~diff[y]&d.holes(target),wrong=(d.hb[t]^d.hb[u.a])&range;
    int lo=wrong?64-__builtin_clzll(wrong):0;if(lo>=c)continue;
    u64 covered=range&low_bits(c)&~low_bits(lo);std::array<int,25>indices{};std::array<double,25>chance{};int n=0;
    for(u64 z=covered;z;z&=z-1){int j=__builtin_ctzll(z);indices[n]=j;chance[n]=prob[j][(d.hb[t]>>j&1)^1];n++;}
    if(n<2)continue;
    std::array<std::array<double,2>,26>left{},right{};left[0][0]=right[n][0]=1;
    for(int i=0;i<n;i++){double p=chance[i];left[i+1]={left[i][0]*(1-p),left[i][1]*(1-p)+left[i][0]*p};}
    for(int i=n-1;i>=0;i--){double p=chance[i];right[i]={right[i+1][0]*(1-p),right[i+1][1]*(1-p)+right[i+1][0]*p};}
    for(int i=0;i<n;i++){int j=indices[i];double p0=left[i][0]*right[i+1][0],p1=left[i][1]*right[i+1][0]+left[i][0]*right[i+1][1];gradient[j]+=beta[y]*(1-p0-.6*p1)*((d.hb[t]>>j&1)?-1:1);}
   }
  }
  return gradient;
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
  if(dynamic)update_probability();
  for(int x=0;x<d.U;x++){auto u=d.unit[x];diff[x]=u.b>=0?d.hb[u.a]^d.hb[u.b]:0;}
  for(int x=0;x<d.U;x++)utility[x]=donor(d.unit[x]);
  std::vector<std::array<int,2>>best(d.H,{-1,-1});
  for(int x=0;x<d.U;x++){auto u=d.unit[x];int b=d.color(u,u.c),&y=best[u.c][b];if(y<0||d.weight(u)>d.weight(d.unit[y])||(d.weight(u)==d.weight(d.unit[y])&&utility[x]>utility[y]))y=x;}
  std::fill(beta.begin(),beta.end(),0);double sum=0;
  for(int c=0;c<d.H;c++)for(int b=0;b<2;b++){int y=best[c][b];assert(y>=0);beta[y]=prob[c][b];sum+=prob[c][b]*utility[y];}
  return sum;
 }
};
MatchStats rematch_tie(Design&d,int iterations,double weight,double strength,bool dynamic,bool derivative){
 auto start=std::chrono::steady_clock::now();MatchStats stats;d.refresh_reset();TieHead head(d,strength,dynamic);double initial=d.cur-weight*head.rebuild(),merit=initial;
 std::mt19937_64 rng(0x181ba71c83ULL);
 for(int it=0;it<iterations;it++){
  std::vector<int>anchor(d.U,-1),mobile(d.U),color(d.U);
  for(int x=0;x<d.U;x++){auto u=d.unit[x];color[x]=d.color(u,u.c);mobile[x]=u.a;if(u.b>=0){anchor[x]=u.b;if(rng()&1)std::swap(anchor[x],mobile[x]);}}
  std::vector<std::array<double,2>>gradient(d.H);
  for(int j=0;j<d.H;j++){
   double x=d.hn[j][0],y=d.hn[j][1],t=d.reset_targets[j],den=std::max(1.,x+y+t),k=4*Design::kHoleWeight,n=x*y+.5*t*std::min(x,y);
   gradient[j]={k*((y+.5*t*(x<=y))*den-n)/(den*den),k*((x+.5*t*(y<x))*den-n)/(den*den)};
  }
  if(derivative){auto g=head.probability_gradient();for(int j=0;j<d.H;j++){double den=std::max(1.,d.hn[j][0]+d.hn[j][1]+strength*d.nt[j]),p=head.prob[j][1];gradient[j][0]+=weight*g[j]*p/den;gradient[j][1]-=weight*g[j]*(1-p)/den;}}
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
