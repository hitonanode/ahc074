struct HandleMarginal {
 std::vector<std::array<double,2>> demand;
 std::vector<double> gradient;
 double seconds=0;
 explicit HandleMarginal(Solver&s,int nsample=16):demand(s.H),gradient(s.H){
  double start=elapsed_sec();Perforation p(s);auto heads=p.choose_heads();
  std::mt19937_64 rng(936270021);
  for(int u=0;u<P;u++){
   int own=s.ded[u],H=s.H;u64 holes=low_bits(H)&~p.opacity[own];
   std::array<std::array<u64,2>,64>ranges{};std::array<std::array<int,2>,64>levels{};
   for(int c=0;c<H;c++)for(int b=0;b<2;b++){
    int k=heads[c][b];u64 mask=p.opacity[k]&holes,wrong=mask&(p.colors[k]^p.target[u]);
    int lo=wrong?64-__builtin_clzll(wrong):0;levels[c][b]=lo;ranges[c][b]=mask&~low_bits(lo);
   }
   auto value=[&](u64 color){
    u64 wrong=(color^p.target[u])&holes;std::array<double,65>dp{};
    for(int c=0;c<H;c++){
     dp[c+1]=dp[c];if(c==p.columns[own])continue;
     for(int b=0;b<2;b++){
      int lo=levels[c][b];u64 covered=wrong&ranges[c][b];int n=__builtin_popcountll(covered);
      double price=1.6+(b!=int(color>>c&1));
      for(int j=lo;j<=c&&n>price;j++){
       dp[c+1]=std::max(dp[c+1],dp[j]+n-price);n-=int(covered>>j&1);
      }
     }
    }
    return __builtin_popcountll(wrong)-dp[H];
   };
   for(int sample=0;sample<nsample;sample++){
    u64 color=0;for(int c=0;c<H;c++)if((rng()>>11)*0x1.0p-53<p.probability[c][1])color|=1ULL<<c;
    double original=value(color);
    for(int c=0;c<H;c++){
     double other=value(color^(1ULL<<c));int b=color>>c&1;
     // Positive gradient means a black column head is more expensive.
     double diff=(b?original-other:other-original)/(P*nsample);
     gradient[c]+=diff;
     if(holes>>c&1){int wanted=p.target[u]>>c&1;demand[c][wanted]+=wanted?-diff:diff;}
    }
   }
  }
  seconds=elapsed_sec()-start;
 }
};
