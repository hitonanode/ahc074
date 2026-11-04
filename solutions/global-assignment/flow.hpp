#include <queue>
struct AssignmentFlow {
 struct Edge{int to,rev,cap;double cost;};std::vector<std::vector<Edge>>g;
 explicit AssignmentFlow(int n):g(n){}
 int add(int a,int b,int cap,double cost){int id=g[a].size(),rev=g[b].size();g[a].push_back({b,rev,cap,cost});g[b].push_back({a,id,0,-cost});return id;}
 void send(int source,int sink,int amount){
  const int n=g.size();std::vector<double>potential(n,1e100),dist(n);std::vector<int>from(n),edge(n);std::vector<bool>queued(n);std::queue<int>q;
  potential[source]=0;q.push(source);queued[source]=true;
  while(!q.empty()){int a=q.front();q.pop();queued[a]=false;for(auto&e:g[a])if(e.cap&&potential[e.to]>potential[a]+e.cost+1e-9){potential[e.to]=potential[a]+e.cost;if(!queued[e.to])q.push(e.to),queued[e.to]=true;}}
  for(auto&x:potential)if(x>1e90)x=0;
  for(int it=0;it<amount;it++){
   dist.assign(n,1e100);dist[source]=0;std::priority_queue<std::pair<double,int>,std::vector<std::pair<double,int>>,std::greater<std::pair<double,int>>>pq;pq.push({0,source});
   while(!pq.empty()){auto[d,a]=pq.top();pq.pop();if(d>dist[a]+1e-9)continue;for(int i=0;i<int(g[a].size());i++){auto&e=g[a][i];if(!e.cap)continue;double next=d+e.cost+potential[a]-potential[e.to];if(next<dist[e.to]-1e-9){dist[e.to]=next;from[e.to]=a;edge[e.to]=i;pq.push({next,e.to});}}}
   assert(dist[sink]<1e90);for(int a=0;a<n;a++)if(dist[a]<1e90)potential[a]+=dist[a];
   for(int a=sink;a!=source;a=from[a]){auto&e=g[from[a]][edge[a]];e.cap--;g[a][e.rev].cap++;}
  }
 }
};
// The retrieval term, apart from the missing-color correction, is
// n(n-1)/2 + .075*n*p + .425*p*p - .5*p. The diagonal quadratic with
// Hessian (1.075, .925) is a tangent upper bound, since the difference
// from its Hessian is .075*(dn-dp)^2. It separates into convex costs of
// all papers n and paired papers p, representable by parallel flow arcs.
bool flow_assignment(Design&d,int&changes){
 auto previous=d.unit;double old=d.cur;int U=d.U,H=d.H;std::vector<std::array<double,2>>derivative(H);
 for(int c=0;c<H;c++){double n=d.hn[c][0]+d.hn[c][1];for(int b=0;b<2;b++)derivative[c][b]=n?4*d.kHoleWeight*std::pow(d.hn[c][b^1]/n,2):d.kHoleWeight;}
 const int first=1+U,sink=first+H*6,source=0;AssignmentFlow f(sink+1);std::vector<std::vector<std::pair<int,int>>>choice(U);std::vector<std::pair<int,int>>required;
 for(int x=0;x<U;x++)f.add(source,1+x,1,0);
 for(int c=0;c<H;c++){
  int base=first+c*6,pairnode=base+4,totalnode=base+5;int p=d.nt[c]-d.nc[c],n=d.nc[c];bool both=d.pairOne[c]>0&&d.pairOne[c]<p;
  std::array<std::array<bool,2>,2>witness{};
  if(both)witness[1][0]=witness[1][1]=true;
  else for(int color=0;color<2;color++){int type=-1;for(auto u:previous)if(u.c==c&&d.color(u,c)==color)type=std::max(type,int(u.b>=0));assert(type>=0);witness[type][color]=true;}
  for(int type=0;type<2;type++)for(int color=0;color<2;color++){
   int a=base+2*type+color,b=type?pairnode:totalnode;if(witness[type][color]){int edge=f.add(a,b,1,-10000);required.emplace_back(a,edge);}f.add(a,b,U,0);
  }
  int maxn=std::min(U,std::max(8,n+4)),maxp=std::min(maxn,p+4);
  for(int t=1;t<=maxp;t++){double marginal=.075*n+.85*p-.5+.925*(t-.5-p);if(!both&&t>1)marginal+=.85;f.add(pairnode,totalnode,1,marginal);}
  for(int t=1;t<=maxn;t++){double marginal=n-.5+.075*p+1.075*(t-.5-n);f.add(totalnode,sink,1,marginal);}
 }
 for(int x=0;x<U;x++){
  auto u=previous[x];int type=u.b>=0;std::vector<double>suffix(H+1);u64 diff=type?d.hb[u.a]^d.hb[u.b]:0;
  for(int c=H-1;c>=0;c--)suffix[c]=suffix[c+1]+((diff>>c&1)?0:d.weight(u)*derivative[c][d.hb[u.a]>>c&1]);
  for(int c=0;c<H;c++)if(d.valid(u,c)){int color=d.color(u,c),edge=f.add(1+x,first+c*6+2*type+color,1,suffix[c+1]+(c==u.c?0:1e-6));choice[x].emplace_back(c,edge);}
 }
 f.send(source,sink,U);for(auto[a,e]:required)assert(f.g[a][e].cap==0);
 for(int x=0;x<U;x++){int assigned=-1;for(auto[c,e]:choice[x])if(!f.g[1+x][e].cap){assert(assigned<0);assigned=c;}assert(assigned>=0);d.unit[x].c=assigned;}
 d.rebuild();assert(d.cur<old+1e-5);
 if(d.cur>=old-1e-7){d.unit=previous;d.rebuild();return false;}for(int x=0;x<U;x++)changes+=d.unit[x].c!=previous[x].c;return true;
}
