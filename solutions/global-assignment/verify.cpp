#include "saved.hpp"
#include "assignment.hpp"
int main(){
 std::mt19937 rng(182734);int checked=0;
 for(int n=2;n<=7;n++)for(int trial=0;trial<50;trial++){
  std::vector<std::vector<double>>cost(n,std::vector<double>(n));
  for(auto&r:cost)for(auto&x:r)x=double(int(rng()%100)-50)/7;
  std::vector<int>p(n);std::iota(p.begin(),p.end(),0);double best=1e100;
  do{double v=0;for(int i=0;i<n;i++)v+=cost[i][p[i]];best=std::min(best,v);}while(std::next_permutation(p.begin(),p.end()));
  auto a=minimum_assignment(cost);double v=0;for(int i=0;i<n;i++)v+=cost[i][a[i]];assert(std::abs(v-best)<1e-8);
  AssignmentFlow f(2*n+2);int source=2*n,sink=source+1;
  for(int i=0;i<n;i++){f.add(source,i,1,0);f.add(n+i,sink,1,0);for(int j=0;j<n;j++)f.add(i,n+j,1,cost[i][j]);}
  f.send(source,sink,n);v=0;for(int i=0;i<n;i++)for(auto&e:f.g[i])if(e.to>=n&&e.to<2*n&&!e.cap)v+=e.cost;
  assert(std::abs(v-best)<1e-8);checked++;
 }
 for(int n=2;n<=15;n++)for(int p=0;p<=n;p++)for(int nn=2;nn<=15;nn++)for(int pp=0;pp<=nn;pp++){
  auto value=[](int n,int p){return .5*n*n-.5*n+.075*n*p+.425*p*p-.5*p;};
  double dn=nn-n,dp=pp-p;
  double bound=value(n,p)+(n-.5+.075*p)*dn+(.075*n+.85*p-.5)*dp+.5*1.075*dn*dn+.5*.925*dp*dp;
  assert(bound+1e-8>=value(nn,pp));checked++;
 }
 std::cout<<"verified assignment/bound cases = "<<checked<<'\n';
}
