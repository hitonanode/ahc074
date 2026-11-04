from pathlib import Path
p=Path(__file__).resolve().parent
s=(p/'dp_search.cpp').read_text()
needle='  for(int j=0;j<G;j++)map.edge[w[j]]=j<int(required.size())?required[j]:rng()%ne,map.color[w[j]]=rng()&1;'
assert needle in s
s=s.replace(needle,needle+'''
  if(ne>=G){std::vector<int> codes(ne);std::iota(codes.begin(),codes.end(),0);std::shuffle(codes.begin(),codes.end(),rng);for(int j=0;j<G;j++)map.edge[w[j]]=codes[j];}
''')
a=s.index(' void choose_mapping(double penalty,double temp){')
s=s[:a]+''' static std::vector<int> rectangular_assignment(const std::vector<std::vector<double>>&a){
  int n=a.size(),m=a[0].size();std::vector<double>u(n+1),v(m+1);std::vector<int>p(m+1),way(m+1);
  for(int i=1;i<=n;i++){
   p[0]=i;int j0=0;std::vector<double>minv(m+1,1e100);std::vector<bool>used(m+1);
   do{
    used[j0]=true;int i0=p[j0],j1=0;double delta=1e100;
    for(int j=1;j<=m;j++)if(!used[j]){double cur=a[i0-1][j-1]-u[i0]-v[j];if(cur<minv[j])minv[j]=cur,way[j]=j0;if(minv[j]<delta)delta=minv[j],j1=j;}
    for(int j=0;j<=m;j++)if(used[j])u[p[j]]+=delta,v[j]-=delta;else minv[j]-=delta;j0=j1;
   }while(p[j0]);
   do{int j1=way[j0];p[j0]=p[j1];j0=j1;}while(j0);
  }
  std::vector<int>result(n);for(int j=1;j<=m;j++)if(p[j])result[p[j]-1]=j-1;return result;
 }
 void choose_unique_mapping(double penalty,double temp){
  std::array<Bits,64>above{};
  for(int t=0;t<256;t++)for(int e=0;e<ne;e++)if(chosen_cmp[t]>>e&1)above[e][t/64]|=1ULL<<(t%64);
  std::vector<std::vector<double>>cost(63,std::vector<double>(ne+63-G));
  std::array<std::array<int,64>,63>polarity{};
  for(int j=0;j<63;j++){
   int total=0;for(U x:care[j])total+=std::popcount(x);
   for(int e=0;e<ne;e++){
    int wrong=0;for(int k=0;k<4;k++)wrong+=std::popcount((above[e][k]^desired[j][k])&care[j][k]);
    double c1=penalty*wrong+noise(temp),c0=penalty*(total-wrong)+noise(temp);
    polarity[j][e]=c1<c0;cost[j][e]=std::min(c0,c1)+.10*total;
   }
   // All handle slots must be used; unused columns are comparison edges.
   double handle=.4*total+noise(temp)-1000000;
   for(int k=ne;k<ne+63-G;k++)cost[j][k]=handle;
  }
  auto assigned=rectangular_assignment(cost);map.edge.fill(-1);int generic=0;
  for(int j=0;j<63;j++)if(assigned[j]<ne){int e=assigned[j];map.edge[j]=e;map.color[j]=polarity[j][e];generic++;}
  assert(generic==G);
 }
'''+s[a:]
s=s.replace(' void choose_mapping(double penalty,double temp){',' void choose_mapping(double penalty,double temp){\n  if(ne>=G){choose_unique_mapping(penalty,temp);return;}')
(p/'unique_search.cpp').write_text(s)
