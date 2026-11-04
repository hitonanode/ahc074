#define main inherited_main
#include "main.cpp"
#undef main
std::vector<double> reference(ProbabilityHead&head){
 auto&d=head.d;auto&utility=head.utility;auto&beta=head.beta;auto&diff=head.diff;auto&prob=head.prob;
  std::vector<double>gradient(d.H);std::vector<std::array<int,2>>selected(d.H,{-1,-1});
  for(int x=0;x<d.U;x++){auto u=d.unit[x];int b=d.color(u,u.c),&y=selected[u.c][b];if(y<0||d.weight(u)>d.weight(d.unit[y])||(d.weight(u)==d.weight(d.unit[y])&&utility[x]>utility[y]))y=x;}
  for(int c=0;c<d.H;c++)gradient[c]=utility[selected[c][1]]-utility[selected[c][0]];
  for(int y=0;y<d.U;y++)if(beta[y]){
   auto u=d.unit[y];int c=u.c;
   for(int t=0;t<P;t++){
    auto target=d.unit[d.owner[t]];if(c==target.c)continue;
    u64 range=low_bits(c+1)&~diff[y]&d.holes(target),wrong=(d.hb[t]^d.hb[u.a])&range;
    int lo=wrong?64-__builtin_clzll(wrong):0;if(lo>=c)continue;
    u64 covered=range&low_bits(c)&~low_bits(lo);std::vector<int>indices(d.H);std::vector<double>chance(d.H);int n=0;
    for(u64 z=covered;z;z&=z-1){int j=__builtin_ctzll(z);indices[n]=j;chance[n]=prob[j][(d.hb[t]>>j&1)^1];n++;}
    if(n<2)continue;
    std::vector<std::array<double,2>>left(d.H+1),right(d.H+1);left[0]={1,0};right[n]={1,0};
    for(int i=0;i<n;i++){double p=chance[i];left[i+1]={left[i][0]*(1-p),left[i][1]*(1-p)+left[i][0]*p};}
    for(int i=n-1;i>=0;i--){double p=chance[i];right[i]={right[i+1][0]*(1-p),right[i+1][1]*(1-p)+right[i+1][0]*p};}
    for(int i=0;i<n;i++){int j=indices[i];double p0=left[i][0]*right[i+1][0],p1=left[i][1]*right[i+1][0]+left[i][0]*right[i+1][1];gradient[j]+=beta[y]*(1-p0-.6*p1)*((d.hb[t]>>j&1)?-1:1);}
   }
  }
  return gradient;
 }
int main(){
 for(int H:{25,31,35}){
  int G=63-H;std::mt19937_64 rng(445100009);std::vector<u64>a(P);for(auto&x:a)x=rng()&kActiveWindows;
  Design d(a,6,G);int target=0;
  for(int x=0;x<d.U;x++){
   int c=x%H,color=(x/H)&1;Design::Unit u{target++,-1,c};if(x<d.need)u.b=target++;
   for(int t:{u.a,u.b})if(t>=0)d.hb[t]=(d.hb[t]&~(1ULL<<c))|(u64(color)<<c);
   d.unit.push_back(u);
  }
  assert(target==P);int donor=5*H-1;
  d.hb[d.unit[0].a]=0;d.hb[d.unit[0].b]=0;d.hb[d.unit[donor].a]=0;
  d.refresh_reset();ProbabilityHead head(d,2,true);head.beta.assign(d.U,0);head.beta[donor]=1;
  auto lhs=head.probability_gradient(),rhs=reference(head);double error=0;
  for(int c=0;c<H;c++)error=std::max(error,std::abs(lhs[c]-rhs[c]));assert(error<1e-10);
  std::cout<<"handles="<<H<<" covered="<<H-2<<" max_error="<<error<<'\n';
 }
}
