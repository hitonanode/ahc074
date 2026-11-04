// A replacement changes all interval edges ending at its own column. Forward
// values up to that column and suffix values after it therefore stay valid.
struct OverlapModel {
 struct Edges { std::array<std::array<double,26>,2> value; };
 struct Record { u64 tb,holes,bad;std::array<double,26> forward;double suffix,without; };
 Design&d;HeadModel simple;int copies;
 std::vector<u64>samples;
 std::vector<std::array<int,2>>heads;
 std::vector<std::vector<Record>>records;
 std::vector<double>loss,target_value;
 std::vector<u64>opaque,black;
 bool cached=false;
 OverlapModel(Design&source,int count):d(source),simple(d),copies(count),samples(P*count),heads(d.H),records(d.U),loss(d.U),target_value(P),opaque(d.U),black(d.U){
  std::mt19937_64 rng(731000003);
  for(auto&v:samples)for(int c=0;c<d.H;c++)if((rng()>>11)*0x1.0p-53<simple.prob[c][1])v|=1ULL<<c;
  rebuild(false);
 }
 std::vector<Edges> edges(int t,u64 holes,u64 colors,int ownercol)const{
  std::vector<Edges> e(d.H);u64 bad=(colors^d.hb[t])&holes;
  for(int c=0;c<d.H;c++)for(int b=0;b<2;b++){
   auto&v=e[c].value[b];v.fill(-1e6);if(c==ownercol)continue;int x=heads[c][b];
   u64 range=opaque[x]&holes,wrong=(black[x]^d.hb[t])&range;
   int lo=wrong?64-__builtin_clzll(wrong):0;if(lo>c)continue;
   u64 covered=bad&range&~low_bits(lo);int count=__builtin_popcountll(covered);double cost=1.6+(b!=int(colors>>c&1));
   for(int s=lo;s<=c;s++){if(count<=cost)break;v[s]=count-cost;count-=int(covered>>s&1);}
  }
  return e;
 }
 double solve(const std::vector<Edges>&e,std::array<double,26>*f=nullptr,std::array<double,26>*back=nullptr)const{
  std::array<double,26>dp{};
  for(int c=0;c<d.H;c++){dp[c+1]=dp[c];for(int b=0;b<2;b++)for(int l=0;l<=c;l++)if(e[c].value[b][l]>0)dp[c+1]=std::max(dp[c+1],dp[l]+e[c].value[b][l]);}
  if(f)*f=dp;
  if(back){back->fill(0);for(int l=d.H-1;l>=0;l--){(*back)[l]=(*back)[l+1];for(int c=l;c<d.H;c++)for(int b=0;b<2;b++)if(e[c].value[b][l]>0)(*back)[l]=std::max((*back)[l],e[c].value[b][l]+(*back)[c+1]);}assert(std::abs((*back)[0]-dp[d.H])<1e-8);}
  return dp[d.H];
 }
 double without(const std::vector<Edges>&e,const std::array<double,26>&f,int c,int b)const{
  auto dp=f;dp[c+1]=dp[c];for(int l=0;l<=c;l++)if(e[c].value[b^1][l]>0)dp[c+1]=std::max(dp[c+1],dp[l]+e[c].value[b^1][l]);
  for(int j=c+1;j<d.H;j++){dp[j+1]=dp[j];for(int color=0;color<2;color++)for(int l=0;l<=j;l++)if(e[j].value[color][l]>0)dp[j+1]=std::max(dp[j+1],dp[l]+e[j].value[color][l]);}
  return dp[d.H];
 }
 double rebuild(bool make_cache){
  cached=make_cache;simple.rebuild();for(auto&r:records)r.clear();std::fill(loss.begin(),loss.end(),0);
  for(int x=0;x<d.U;x++){auto u=d.unit[x];opaque[x]=low_bits(u.c+1)&~simple.diff[x];black[x]=d.hb[u.a];if(simple.beta[x])heads[u.c][d.color(u,u.c)]=x;}
  double total=0;
  for(int t=0;t<P;t++){
   auto u=d.unit[d.owner[t]];u64 holes=d.holes(u);double sum=0;
   for(int s=0;s<copies;s++){
    u64 colors=samples[t*copies+s];auto e=edges(t,holes,colors,u.c);std::array<double,26>fw{},bw{};double base=solve(e,&fw,make_cache?&bw:nullptr);sum+=base;
    if(make_cache)for(int c=0;c<d.H;c++)if(c!=u.c)for(int b=0;b<2;b++){
     int x=heads[c][b];double excluded=without(e,fw,c,b);loss[x]+=excluded-base;
     Record r{d.hb[t],holes,(colors^d.hb[t])&holes,fw,bw[c+1],excluded};
     // Encode the fixed retrieval price by reducing the unchanged suffix.
     r.suffix-=1.6+(b!=int(colors>>c&1));records[x].push_back(r);
    }
   }
   target_value[t]=sum/copies;total+=target_value[t];
  }
  return total;
 }
 double target(int t,const Design::Unit&u)const{
  u64 holes=d.holes(u);double total=0;
  for(int s=0;s<copies;s++)total+=solve(edges(t,holes,samples[t*copies+s],u.c));
  return total/copies-target_value[t];
 }
 __attribute__((target("popcnt"))) double donor(const Design::Unit&u,int slot)const{
  assert(cached);u64 op=low_bits(u.c+1)&~(u.b>=0?d.hb[u.a]^d.hb[u.b]:0),yb=d.hb[u.a];double sum=loss[slot];
  for(auto&r:records[slot]){
   u64 range=op&r.holes,wrong=(yb^r.tb)&range;int lo=wrong?64-__builtin_clzll(wrong):0;if(lo>u.c)continue;
   u64 covered=range&r.bad&~low_bits(lo);int count=__builtin_popcountll(covered);double best=0;
   for(int l=lo;l<=u.c;l++){best=std::max(best,r.forward[l]+count+r.suffix-r.without);count-=int(covered>>l&1);}
   sum+=best;
  }
  return sum/copies;
 }
 void check(){
  assert(cached);
  for(int x=0;x<d.U;x++)if(simple.beta[x])assert(std::abs(donor(d.unit[x],x))<1e-7);
  for(int t=0;t<P;t++)assert(std::abs(target(t,d.unit[d.owner[t]]))<1e-7);
 }
};
