struct OverlapDesign {
 Design&d;int copies;double coefficient;
 std::vector<u64> differences,samples;
 std::vector<std::array<double,26>> q;
 std::vector<double> utility;
 std::vector<std::vector<int>> members;
 std::vector<std::array<int,2>> max_weight,heads;
 int accepted=0,tried=0;double before=0,after=0,seconds=0;
 XorShift rng{0x21e87ab4a3ULL};
 OverlapDesign(Design&source,int count,double weight):d(source),copies(count),coefficient(weight){
  differences.resize(d.U);for(int x=0;x<d.U;x++)if(d.unit[x].b>=0)differences[x]=d.hb[d.unit[x].a]^d.hb[d.unit[x].b];
  q.resize(P);std::vector<double>prob(d.H);
  for(int c=0;c<d.H;c++){double n=d.hn[c][0]+d.hn[c][1];prob[c]=n?d.hn[c][1]/n:.5;}
  for(int t=0;t<P;t++)for(int c=0;c<d.H;c++)q[t][c+1]=q[t][c]+2*((d.hb[t]>>c&1)?1-prob[c]:prob[c]);
  std::mt19937_64 random(731000003);samples.resize(P*copies);
  for(auto&bits:samples)for(int c=0;c<d.H;c++)if((random()>>11)*0x1.0p-53<prob[c])bits|=1ULL<<c;
  utility.resize(d.U);members.resize(d.H);max_weight.resize(d.H);heads.resize(d.H);
  for(int x=0;x<d.U;x++){
   int c=d.unit[x].c,b=d.color(d.unit[x],c);members[c].push_back(x);max_weight[c][b]=std::max(max_weight[c][b],d.weight(d.unit[x]));
   for(int t=0;t<P;t++)utility[x]+=gain(t,x,c);
  }
 }
 double gain(int t,int y,int c)const{return Design::filler_gain(d.hb[t],d.unit[d.owner[t]].c,differences[d.owner[t]],d.hb[d.unit[y].a],differences[y],c,q[t].data());}
 void choose_heads(){
  for(int c=0;c<d.H;c++){
   heads[c]={-1,-1};
   for(int x:members[c]){int b=d.color(d.unit[x],c);if(d.weight(d.unit[x])==max_weight[c][b]&&(heads[c][b]<0||utility[x]>utility[heads[c][b]]))heads[c][b]=x;}
   assert(heads[c][0]>=0&&heads[c][1]>=0);
  }
 }
 // Each edge is an interval covered by one visible head (or the opposite
 // head after one dig). Non-overlapping edges form a legal subset of fillers.
 __attribute__((target("popcnt"))) double value(){
  choose_heads();double sum=0;
  std::vector<u64>opaque(d.U);for(int x=0;x<d.U;x++)opaque[x]=low_bits(d.unit[x].c+1)&~differences[x];
  for(int t=0;t<P;t++){
   int owner=d.owner[t];u64 holes=d.holes(d.unit[owner]);
   std::array<std::array<u64,2>,25>ranges{};std::array<std::array<int,2>,25>level{};
   for(int c=0;c<d.H;c++)for(int b=0;b<2;b++){
    int x=heads[c][b];u64 range=opaque[x]&holes;
    u64 wrong=(d.hb[d.unit[x].a]^d.hb[t])&range;
    ranges[c][b]=range;level[c][b]=wrong?64-__builtin_clzll(wrong):0;
   }
   for(int sample=0;sample<copies;sample++){
    u64 color=samples[t*copies+sample],bad=(color^d.hb[t])&holes;
    std::array<double,26>forward{};
    for(int c=0;c<d.H;c++){
     forward[c+1]=forward[c];if(c==d.unit[owner].c)continue;
     for(int b=0;b<2;b++){
      int lo=level[c][b];u64 covered=bad&ranges[c][b]&~low_bits(lo);
      int number=__builtin_popcountll(covered);double cost=1.6+(b!=int(color>>c&1));
      if(number<=cost)continue;
      for(int start=lo;start<=c;start++){
       forward[c+1]=std::max(forward[c+1],forward[start]+number-cost);
       number-=int(covered>>start&1);if(number<=cost)break;
      }
     }
    }
    sum+=forward[d.H];
   }
  }
  return sum/copies;
 }
 void climb(int iterations){
  auto start=std::chrono::steady_clock::now();double proxy=value();before=proxy/P;
  for(int it=0;it<iterations;it++){
   int x=rng.below(d.U),y=rng.below(d.U),a=d.unit[x].c,b=d.unit[y].c;
   if(a==b||(d.unit[x].b>=0)!=(d.unit[y].b>=0))continue;
   auto ox=d.unit[x],oy=d.unit[y],nx=ox,ny=oy;nx.c=b;ny.c=a;
   if(!d.valid(nx,b)||!d.valid(ny,a)||d.color(nx,b)!=d.color(oy,b)||d.color(ny,a)!=d.color(ox,a))continue;
   tried++;std::vector<int>moved;for(int t:{ox.a,ox.b,oy.a,oy.b})if(t>=0)moved.push_back(t);
   auto old_utility=utility;
   for(int z=0;z<d.U;z++)if(z!=x&&z!=y)for(int t:moved)utility[z]-=gain(t,z,d.unit[z].c);
   d.unit[x]=nx;d.unit[y]=ny;utility[x]=utility[y]=0;
   for(int t=0;t<P;t++){utility[x]+=gain(t,x,b);utility[y]+=gain(t,y,a);}
   for(int z=0;z<d.U;z++)if(z!=x&&z!=y)for(int t:moved)utility[z]+=gain(t,z,d.unit[z].c);
   auto ix=std::find(members[a].begin(),members[a].end(),x),iy=std::find(members[b].begin(),members[b].end(),y);*ix=y;*iy=x;
   double next=value(),old=d.cur;d.update(ox,-1);d.update(oy,-1);d.update(nx,1);d.update(ny,1);
   if(d.cur-old-coefficient*(next-proxy)<-1e-8){accepted++;proxy=next;}
   else{
    d.update(nx,-1);d.update(ny,-1);d.update(ox,1);d.update(oy,1);d.cur=old;
    d.unit[x]=ox;d.unit[y]=oy;*ix=x;*iy=y;utility=std::move(old_utility);
   }
  }
  after=proxy/P;double saved=d.cur;d.rebuild();assert(std::abs(saved-d.cur)<1e-6);
  for(int y=0;y<d.U;y++){double exact=0;for(int t=0;t<P;t++)exact+=gain(t,y,d.unit[y].c);assert(std::abs(exact-utility[y])<1e-7);}
  assert(std::abs(value()/P-after)<1e-7);
  seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();
 }
};
