from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'search.cpp').read_text()
s=s.replace('std::array<unsigned char,9>','std::array<unsigned char,12>')
s=s.replace('std::array<int,9>','std::array<int,12>')
s=s.replace('std::array<unsigned,9>','std::array<unsigned,12>')
s=s.replace('std::array<std::array<U,2>,36>','std::array<std::array<U,2>,64>')
s=s.replace('std::array<Bits,36>','std::array<Bits,64>')
s=s.replace('std::array<std::array<int,36>,63>','std::array<std::array<int,64>,63>')
s=s.replace(' std::array<int,256>chosen{};',' std::array<int,256>chosen{};std::array<U,256>chosen_cmp{};std::vector<int>required;')
s=s.replace('unsigned seed):M(m)','unsigned seed,int triple_limit=-1):M(m)')
s=s.replace('assert(M<=9&&G>=ne&&G<=63);','assert(M<=11&&G>=M*(M-1)/2-(M>8?1000:0)&&G<=63);')
needle='  // Two additional generic papers require two additional merges compared with'
a=s.index(needle)
s=s[:a]+'''  if(triple_limit>=0){
   int nt=0;for(auto&x:groups)nt+=x.targets.size()==3;
   while(nt>triple_limit){
    int chosen=-1,largest=-1;
    for(int i=0;i<int(groups.size());i++)if(groups[i].targets.size()==3){
     auto t=groups[i].targets;int d=std::popcount((A[t[0]]^A[t[1]])|(A[t[0]]^A[t[2]]));
     if(d>largest)largest=d,chosen=i;
    }
    auto t=groups[chosen].targets;int a=0,b=1,distance=100;
    for(int i=0;i<3;i++)for(int j=i+1;j<3;j++)if(std::popcount(A[t[i]]^A[t[j]])<distance)distance=std::popcount(A[t[i]]^A[t[j]]),a=i,b=j;
    groups[chosen].targets={t[a],t[b]};groups.push_back(Group{{t[3-a-b]},0});nt--;
   }
  }
'''+s[a:]
s=s.replace('  std::array<unsigned char,12>p0{};','  if(M<=8){std::array<unsigned char,12>p0{};')
s=s.replace('  map.edge.fill(-1);std::vector<int>w(63);','  }\n  for(int e=0;e<ne;e++){auto[a,b]=edges[e];if(M<=8||b<6||(a<6&&(a==(b-6)%6||a==(b-5)%6)))required.push_back(e);}\n  assert(int(required.size())<=G);\n  map.edge.fill(-1);std::vector<int>w(63);')
s=s.replace('map.edge[w[j]]=j%ne,map.color[w[j]]=rng()&1;','map.edge[w[j]]=j<int(required.size())?required[j]:rng()%ne,map.color[w[j]]=rng()&1;')
s=s.replace('if(M<=8||b<6||','if(ne<=G||b<6||')
a=s.index(' // Minimum number of violated windows')
b=s.index(' double group_score(',a)
s=s[:a]+''' // Subset DP computes the exact error optimum. Weighted counts of optimal
 // and near-optimal extensions sample the same Boltzmann distribution as
 // exhaustive permutation enumeration, without constructing M! states.
 std::pair<int,U> order_info(int target,U holes,double temperature,bool sample){
  int NS=1<<M;std::array<std::array<int,12>,12>w{};
  for(U z=holes&generic_mask();z;z&=z-1){int j=std::countr_zero(z);auto[a,b]=edges[map.edge[j]];if((A[target]>>j&1)!=unsigned(map.color[j]))std::swap(a,b);w[a][b]++;}
  std::vector<int>row(M*NS),dp(NS);
  for(int v=0;v<M;v++)for(unsigned mask=1;mask<unsigned(NS);mask++){int u=std::countr_zero(mask);row[v*NS+mask]=row[v*NS+(mask&(mask-1))]+w[v][u];}
  std::vector<double>count(sample?NS:0);if(sample)count[0]=1;
  std::array<double,128>factor{};factor[0]=1;
  if(sample&&temperature>1e-9)for(int i=1;i<128;i++)factor[i]=std::exp(-i/temperature);
  for(unsigned mask=1;mask<unsigned(NS);mask++){
   int best=100000;for(unsigned z=mask;z;z&=z-1){int v=std::countr_zero(z);unsigned rest=mask^(1U<<v);best=std::min(best,dp[rest]+row[v*NS+rest]);}dp[mask]=best;
   if(sample)for(unsigned z=mask;z;z&=z-1){int v=std::countr_zero(z);unsigned rest=mask^(1U<<v);count[mask]+=count[rest]*factor[dp[rest]+row[v*NS+rest]-best];}
  }
  if(!sample)return {dp.back(),0};
  std::array<int,12>pos{};unsigned mask=NS-1;int position=M-1;
  while(mask){
   double skip=uniform()*count[mask];int last=-1;
   for(unsigned z=mask;z;z&=z-1){int v=std::countr_zero(z);unsigned rest=mask^(1U<<v);double weight=count[rest]*factor[dp[rest]+row[v*NS+rest]-dp[mask]];last=v;if(skip<weight)break;skip-=weight;}
   pos[last]=position--;mask^=1U<<last;
  }
  U cmp=0;for(int e=0;e<ne;e++)if(pos[edges[e].first]<pos[edges[e].second])cmp|=1ULL<<e;
  return {dp.back(),cmp};
 }
 int minimum_errors(int target,U holes){return order_info(target,holes,0,false).first;}
'''+s[b:]
s=s.replace('double group_score(Group&x,double penalty)const','double group_score(Group&x,double penalty)')
a=s.index(' void choose_orders(double temp){')
b=s.index(' static std::vector<int> assignment(',a)
s=s[:a]+''' void choose_orders(double temp){
  U gm=generic_mask();
  for(auto&x:groups)if(x.targets.size()>1){
   if(x.targets.size()==2){int a=x.targets[0],b=x.targets[1];chosen_cmp[a]=order_info(a,x.diff&gm,temp*.5,true).second;chosen_cmp[b]=((1ULL<<ne)-1)^chosen_cmp[a];}
   else for(int t:x.targets)chosen_cmp[t]=order_info(t,x.diff&gm,temp,true).second;
  }
 }
'''+s[b:]
s=s.replace('comparisons[chosen[t]]>>e&1','chosen_cmp[t]>>e&1')
s=s.replace('std::array<std::array<double,63>,63>cost{};','std::array<std::array<double,63>,63>cost{};int nr=required.size();')
s=s.replace('int b=c1<c0;polarity[j][e]=b;cost[j][e]=std::min(c0,c1)+.10*total;\n    if(cost[j][e]<minimum)minimum=cost[j][e],be=e;',
'''int b=c1<c0;polarity[j][e]=b;double value=std::min(c0,c1)+.10*total;
    for(int k=0;k<nr;k++)if(required[k]==e)cost[j][k]=value;
    if(value<minimum)minimum=value,be=e;''')
s=s.replace('for(int k=ne;k<G;k++)','for(int k=nr;k<G;k++)')
s=s.replace('int e=assigned[j]<ne?assigned[j]:bestedge[j];','int e=assigned[j]<nr?required[assigned[j]]:bestedge[j];')
s=s.replace('int min=64;for(U show:display)min=std::min(min,std::popcount((show^A[t])&x.diff&gm));err+=min;','err+=minimum_errors(t,x.diff&gm);')
s=s.replace('bool joint=argc>6?std::stoi(argv[6]):false;','bool joint=argc>6?std::stoi(argv[6]):false;int triples=argc>7?std::stoi(argv[7]):-1;')
s=s.replace('Latent x(argv[1],M,G,seed);','Latent x(argv[1],M,G,seed,triples);')
s=s.replace('std::cout<<"]}\\\\n";','std::cout<<"]}\\\\n";')
s=s.replace(' std::cout<<"]}\\n";',' std::cout<<"]}\\n";')
s=s.replace(' std::cout<<"]}\\n";', ''' std::cout<<"],\\"groups\\":[";
 for(int i=0;i<int(x.groups.size());i++){if(i)std::cout<<',';std::cout<<'[';for(int j=0;j<int(x.groups[i].targets.size());j++)std::cout<<(j?",":"")<<x.groups[i].targets[j];std::cout<<']';}
 std::cout<<"]}\\n";return 0;''')
(p/'dp_search.cpp').write_text(s)
