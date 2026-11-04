#include <algorithm>
#include <vector>
#include <numeric>
#include <random>
#include <iostream>
#include <functional>
#include <cassert>
#include "matching.hpp"
int main(){
 std::mt19937 rng(829173);int checked=0;
 for(int n=2;n<=10;n++)for(int trial=0;trial<300;trial++){
  CardinalMatching m(n);std::vector<unsigned>adj(n);
  for(int a=0;a<n;a++)for(int b=a+1;b<n;b++)if(rng()%3==0){m.g[a].push_back(b);m.g[b].push_back(a);adj[a]|=1U<<b;adj[b]|=1U<<a;}
  std::vector<int>dp(1U<<n,-1);std::function<int(unsigned)>solve=[&](unsigned mask){if(!mask)return 0;int&ans=dp[mask];if(ans>=0)return ans;int a=__builtin_ctz(mask);unsigned rest=mask&~(1U<<a);ans=solve(rest);for(unsigned z=adj[a]&rest;z;z&=z-1)ans=std::max(ans,1+solve(rest&~(z&-z)));return ans;};
  // Random initial edges exercise the supplied-matching path as well.
  if(trial%2)for(int a=0;a<n;a++)if(m.match[a]<0)for(int b:m.g[a])if(m.match[b]<0&&rng()%2){m.match[a]=b;m.match[b]=a;break;}
  for(int a=0;a<n;a++)if(m.match[a]<0)m.augment(a);
  int count=0;for(int a=0;a<n;a++)if(m.match[a]>=0){int b=m.match[a];assert(m.match[b]==a&&(adj[a]>>b&1));count++;}
  assert(count/2==solve((1U<<n)-1));checked++;
 }
 std::cout<<"verified maximum matchings = "<<checked<<'\n';
}
