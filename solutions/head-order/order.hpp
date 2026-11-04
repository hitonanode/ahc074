struct OrderStats {int trials=0,accepted=0;double change=0,seconds=0;};
OrderStats order_head(Design&d,int passes,int distance){
 auto start=std::chrono::steady_clock::now();OrderStats stats;d.refresh_reset();ProbabilityHead h(d,2,true);double value=d.cur-h.rebuild(),initial=value;
 auto swap=[&](int a,int b){
  std::swap(d.handle[a],d.handle[b]);for(auto&v:d.hb){u64 z=((v>>a)^(v>>b))&1;v^=(z<<a)|(z<<b);}
  for(auto&u:d.unit){if(u.c==a)u.c=b;else if(u.c==b)u.c=a;}d.refresh_reset();
 };
 std::mt19937_64 rng(73920371);std::vector<std::pair<int,int>>pairs;
 for(int a=0;a<d.H;a++)for(int b=a+1;b<d.H&&b<=a+distance;b++)pairs.emplace_back(a,b);
 for(int pass=0;pass<passes;pass++){
  std::shuffle(pairs.begin(),pairs.end(),rng);int before=stats.accepted;
  for(auto[a,b]:pairs){
   stats.trials++;swap(a,b);double next=d.cur-h.rebuild();
   if(next<value-1e-7){value=next;stats.accepted++;}else{swap(a,b);h.rebuild();}
  }
  if(stats.accepted==before)break;
 }
 stats.change=(value-initial)/P;stats.seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();return stats;
}
