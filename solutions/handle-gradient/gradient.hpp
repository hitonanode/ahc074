std::vector<double> head_gradient(Solver&s){
 Perforation p(s);auto heads=p.choose_heads();std::vector<double>g(s.H),utility(K);
 for(int c=0;c<s.H;c++)for(int b=0;b<2;b++){
  int k=heads[c][b];double beta=p.probability[c][b];
  for(int u=0;u<P;u++){
   if(p.columns[s.ded[u]]==c)continue;
   utility[k]+=p.gain(u,k);
   u64 range=p.opacity[k]&~p.opacity[s.ded[u]],wrong=range&(p.colors[k]^p.target[u]);
   int lo=wrong?64-__builtin_clzll(wrong):0;u64 cover=range&low_bits(c)&~low_bits(lo);
   std::array<int,64>indices{};std::array<double,64>chance{};int n=0;
   for(u64 z=cover;z;z&=z-1){int j=__builtin_ctzll(z);indices[n]=j;chance[n]=p.probability[j][(p.target[u]>>j&1)^1];n++;}
   if(n<2)continue;
   std::array<std::array<double,2>,65>left{},right{};left[0][0]=right[n][0]=1;
   for(int i=0;i<n;i++){double q=chance[i];left[i+1]={left[i][0]*(1-q),left[i][1]*(1-q)+left[i][0]*q};}
   for(int i=n-1;i>=0;i--){double q=chance[i];right[i]={right[i+1][0]*(1-q),right[i+1][1]*(1-q)+right[i+1][0]*q};}
   for(int i=0;i<n;i++){
    int j=indices[i];double p0=left[i][0]*right[i+1][0],p1=left[i][1]*right[i+1][0]+left[i][0]*right[i+1][1];
    g[j]+=beta*(1-p0-.6*p1)*((p.target[u]>>j&1)?-1:1)/P;
   }
  }
 }
 for(int c=0;c<s.H;c++)g[c]+=(utility[heads[c][1]]-utility[heads[c][0]])/P;
 return g;
}
