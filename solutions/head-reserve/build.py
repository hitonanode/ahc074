from pathlib import Path
p=Path(__file__).resolve().parent
s=(p.parent/'tight-thirty-eight/main.cpp').read_text()
s=s.replace('static constexpr double head_mix = 1.0;','static constexpr double head_mix = 1.0;\n    static inline double reserve_head=0;')
old='            std::array<double,2>sum{},best{};std::array<int,2>count{};\n            for(int y:members[c]){int b=color(unit[y],c);sum[b]+=utility[y];count[b]++;if(weight(unit[y])==max_weight[c][b])best[b]=std::max(best[b],utility[y]);}\n            double value=0;for(int b=0;b<2;b++)if(count[b])value+=color_probability[c][b]*((1-head_mix)*sum[b]/count[b]+head_mix*best[b]);'
new='            std::array<double,2>sum{},best{},second{};std::array<int,2>count{},eligible{};\n            for(int y:members[c]){int b=color(unit[y],c);sum[b]+=utility[y];count[b]++;\n                if(weight(unit[y])==max_weight[c][b]){eligible[b]++;if(utility[y]>best[b])second[b]=best[b],best[b]=utility[y];else second[b]=std::max(second[b],utility[y]);}\n            }\n            double value=0;for(int b=0;b<2;b++)if(count[b]){\n                double top=best[b];if(eligible[b]>1)top=(1-reserve_head)*best[b]+reserve_head*second[b];\n                value+=color_probability[c][b]*((1-head_mix)*sum[b]/count[b]+head_mix*top);\n            }'
assert s.count(old)==1;s=s.replace(old,new)
marker=' double rebuild(){\n  if(dynamic)update_probability();'
addition=' // The backup head must have the same maximum direct request frequency.\n std::vector<std::array<std::array<int,2>,2>> best_two()const{\n  std::vector<std::array<std::array<int,2>,2>>best(d.H);for(auto&r:best)for(auto&x:r)x={-1,-1};\n  for(int x=0;x<d.U;x++){\n   auto u=d.unit[x];auto&v=best[u.c][d.color(u,u.c)];int a=v[0];\n   if(a<0||d.weight(u)>d.weight(d.unit[a]))v={x,-1};\n   else if(d.weight(u)==d.weight(d.unit[a])){\n    if(utility[x]>utility[a])v={x,a};\n    else if(v[1]<0||utility[x]>utility[v[1]])v[1]=x;\n   }\n  }\n  return best;\n }\n double top_value(const std::array<int,2>&v)const{\n  assert(v[0]>=0);return v[1]<0?utility[v[0]]:(1-Design::reserve_head)*utility[v[0]]+Design::reserve_head*utility[v[1]];\n }\n'
assert s.count(marker)==1;s=s.replace(marker,addition+marker)
a=s.index('  std::vector<std::array<int,2>>best(d.H,{-1,-1});',s.index('struct ProbabilityHead'))
b=s.index('  return sum;',a)
s=s[:a]+'  auto best=best_two();\n  std::fill(beta.begin(),beta.end(),0);double sum=0;\n  for(int c=0;c<d.H;c++)for(int b=0;b<2;b++){\n   const auto&v=best[c][b];assert(v[0]>=0);double share=v[1]<0?0:Design::reserve_head;\n   beta[v[0]]=prob[c][b]*(1-share);if(v[1]>=0)beta[v[1]]=prob[c][b]*share;\n   sum+=prob[c][b]*top_value(v);\n  }\n'+s[b:]
a=s.index('  std::vector<double>gradient(d.H);',s.index('struct ProbabilityHead'))
b=s.index('  for(int y=0;y<d.U;y++)if(beta[y]){',a)
s=s[:a]+'  std::vector<double>gradient(d.H);auto selected=best_two();\n  for(int c=0;c<d.H;c++)gradient[c]=top_value(selected[c][1])-top_value(selected[c][0]);\n'+s[b:]
(p/'main.cpp').write_text(s)
