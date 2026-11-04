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
#include "flow.hpp"
struct GlobalAssignment {
 bool relaxed=false;
 bool flow=false;
 int unit_changes=0,handle_changes=0,rounds=0;double before=0,after=0,seconds=0;
 bool units(Design&d){
  auto previous=d.unit;double old=d.cur;std::vector<std::array<double,2>>derivative(d.H);
  std::vector<int>required(d.U,-1);
  for(int c=0;c<d.H;c++){
   std::array<int,2>any{-1,-1},paired{-1,-1};for(int x=0;x<d.U;x++)if(previous[x].c==c){int color=d.color(previous[x],c);any[color]=x;if(previous[x].b>=0)paired[color]=x;}
   for(int color=0;color<2;color++){int x=paired[0]>=0&&paired[1]>=0?paired[color]:any[color];assert(x>=0);required[x]=color;}
  }
  for(int c=0;c<d.H;c++){double n=d.hn[c][0]+d.hn[c][1];for(int b=0;b<2;b++)derivative[c][b]=n?4*d.kHoleWeight*std::pow(d.hn[c][b^1]/n,2):d.kHoleWeight;}
  for(int type=0;type<2;type++){
   std::vector<int>ids;for(int x=0;x<d.U;x++)if((d.unit[x].b>=0)==type)ids.push_back(x);int n=ids.size();std::vector<std::vector<double>>cost(n,std::vector<double>(n,1e8));
   for(int i=0;i<n;i++){auto unit=previous[ids[i]];std::vector<double>suffix(d.H+1);
    u64 diff=unit.b<0?0:d.hb[unit.a]^d.hb[unit.b];for(int c=d.H-1;c>=0;c--)suffix[c]=suffix[c+1]+((diff>>c&1)?0:d.weight(unit)*derivative[c][d.hb[unit.a]>>c&1]);
    for(int j=0;j<n;j++){auto slot=previous[ids[j]];int c=slot.c,req=relaxed?required[ids[j]]:d.color(slot,c);if(d.valid(unit,c)&&(req<0||d.color(unit,c)==req))cost[i][j]=suffix[c+1]+(i==j?0:1e-6);}
   }
   auto assignment=minimum_assignment(cost);for(int i=0;i<n;i++){assert(cost[i][assignment[i]]<1e7);d.unit[ids[i]].c=previous[ids[assignment[i]]].c;}
  }
  d.rebuild();assert(d.cur<old+1e-5);
  if(d.cur>=old-1e-7){d.unit=previous;d.rebuild();return false;}
  for(int x=0;x<d.U;x++)unit_changes+=d.unit[x].c!=previous[x].c;return true;
 }
 bool handles(Design&d){
  auto old_handle=d.handle;double old=d.cur;std::vector<std::vector<double>>cost(d.H,std::vector<double>(d.H,1e8));
  for(int c=0;c<d.H;c++)for(int j=0;j<d.H;j++){
   int n0=0,n1=0,ones=0,pairones=0;bool valid=true;
   for(auto u:d.unit){int a=d.hb[u.a]>>j&1,b=u.b<0?a:int(d.hb[u.b]>>j&1);if(u.c==c){if(a!=b){valid=false;break;}ones+=a;pairones+=a*(u.b>=0);}
    if(u.c<c||a!=b){(a?n1:n0)++;if(u.b>=0)(b?n1:n0)++;}
   }
   if(valid)cost[c][j]=d.colcost_of(d.nc[c],d.nt[c],ones,pairones)+d.hole_table()[n0*257+n1]+(c==j?0:1e-6);
  }
  auto assignment=minimum_assignment(cost);for(int c=0;c<d.H;c++){assert(cost[c][assignment[c]]<1e7);d.handle[c]=old_handle[assignment[c]];}
  for(int a=0;a<P;a++){d.hb[a]=0;for(int c=0;c<d.H;c++)d.hb[a]|=((d.A[a]>>d.handle[c])&1)<<c;}
  d.rebuild();assert(d.cur<old+1e-5);
  if(d.cur>=old-1e-7){d.handle=old_handle;for(int a=0;a<P;a++){d.hb[a]=0;for(int c=0;c<d.H;c++)d.hb[a]|=((d.A[a]>>d.handle[c])&1)<<c;}d.rebuild();return false;}
  for(int c=0;c<d.H;c++)handle_changes+=d.handle[c]!=old_handle[c];return true;
 }
 void optimize(Design&d,int max_rounds){auto start=std::chrono::steady_clock::now();before=d.cur/P;for(int it=0;it<max_rounds;it++){bool a=flow?flow_assignment(d,unit_changes):units(d),b=handles(d);rounds++;if(!a&&!b)break;}after=d.cur/P;seconds=CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count();}
};
