#include "saved.hpp"
int main(){
 Design d(std::vector<u64>(P),6,38);int tests=0;
 for(int n=2;n<=8;n++)for(int a=0;a<=n;a++)for(int b=0;b+a<=n;b++)for(int c=0;a+b+c<=n;c++){
  int e=n-a-b-c; // Counts: white single, black single, white pair, black pair.
  int ones=b+e,pairs=c+e;if(!ones||ones==n)continue;
  std::vector<int>order;for(int i=0;i<a;i++)order.push_back(0);for(int i=0;i<b;i++)order.push_back(1);for(int i=0;i<c;i++)order.push_back(2);for(int i=0;i<e;i++)order.push_back(3);
  std::array<int,2>best{1000000,1000000};
  do{if((order[0]&1)==(order[1]&1))continue;int value=0;for(int j=0;j<n;j++)value+=j*(1+(order[j]>=2));best[order[0]&1]=std::min(best[order[0]&1],value);}while(std::next_permutation(order.begin(),order.end()));
  for(int p:{0,10,20,30,40}){
   d.first_black40[d.handle[0]]=p;d.first_white40[d.handle[0]]=40-p;
   double expected=((40-p)*best[0]+p*best[1])/40.;
   double model=Design::colcost_of(n,n+pairs,ones,e)+d.color_rank40(0,n,n+pairs,e)/40.;
   assert(std::abs(expected-model)<1e-9);tests++;
  }
 }
 std::cout<<tests<<" exact weighted-depth checks passed\n";
}
