// Exact minimum cost assignment: row i is sent to result[i]. All callers have
// the current valid arrangement as a feasible assignment, including sparse edges.
std::vector<int> minimum_assignment(const std::vector<std::vector<double>>&cost){
 int n=cost.size();std::vector<double>u(n+1),v(n+1);std::vector<int>p(n+1),way(n+1);
 for(int i=1;i<=n;i++){
  p[0]=i;int j0=0;std::vector<double>mn(n+1,1e100);std::vector<bool>used(n+1);
  do{used[j0]=true;int i0=p[j0],j1=0;double delta=1e100;for(int j=1;j<=n;j++)if(!used[j]){double cur=cost[i0-1][j-1]-u[i0]-v[j];if(cur<mn[j])mn[j]=cur,way[j]=j0;if(mn[j]<delta)delta=mn[j],j1=j;}
   for(int j=0;j<=n;j++)if(used[j])u[p[j]]+=delta,v[j]-=delta;else mn[j]-=delta;j0=j1;
  }while(p[j0]);
  do{int j1=way[j0];p[j0]=p[j1];j0=j1;}while(j0);
 }
 std::vector<int>ans(n);for(int j=1;j<=n;j++)ans[p[j]-1]=j-1;return ans;
}

// Edmonds' alternating-path search, starting from any valid partial matching.
// Neighbor order only chooses among augmenting paths; odd cycles are contracted.
struct CardinalMatching {
 int n;std::vector<std::vector<int>>g;std::vector<int>match,parent,base,queue;
 std::vector<unsigned char>used,blossom;
 explicit CardinalMatching(int size):n(size),g(n),match(n,-1),parent(n),base(n),queue(n),used(n),blossom(n){}
 int lca(int a,int b){
  std::vector<unsigned char>path(n);
  while(true){a=base[a];path[a]=1;if(match[a]<0)break;a=parent[match[a]];}
  while(true){b=base[b];if(path[b])return b;b=parent[match[b]];}
 }
 void mark(int v,int root,int child){
  while(base[v]!=root){blossom[base[v]]=blossom[base[match[v]]]=1;parent[v]=child;child=match[v];v=parent[match[v]];}
 }
 bool augment(int root){
  std::fill(used.begin(),used.end(),0);std::fill(parent.begin(),parent.end(),-1);std::iota(base.begin(),base.end(),0);
  int begin=0,end=0;queue[end++]=root;used[root]=1;
  while(begin<end){int v=queue[begin++];for(int u:g[v]){
   if(base[v]==base[u]||match[v]==u)continue;
   if(u==root||(match[u]>=0&&parent[match[u]]>=0)){
    int b=lca(v,u);std::fill(blossom.begin(),blossom.end(),0);mark(v,b,u);mark(u,b,v);
    for(int i=0;i<n;i++)if(blossom[base[i]]){base[i]=b;if(!used[i])used[i]=1,queue[end++]=i;}
   }else if(parent[u]<0){
    parent[u]=v;
    if(match[u]<0){for(int a=u;a>=0;){int b=parent[a],next=b<0?-1:match[b];match[a]=b;if(b>=0)match[b]=a;a=next;}return true;}
    u=match[u];used[u]=1;queue[end++]=u;
   }
  }}return false;
 }
};
