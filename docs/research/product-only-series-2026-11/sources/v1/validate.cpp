// Independent replay validator. No solver code is included.
#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <stdexcept>
#include <string>
#include <vector>
using U=uint64_t;
int main(int argc,char**argv){
 try{
  if(argc!=3)throw std::runtime_error("usage: validate input output");
  std::ifstream in(argv[1]),out(argv[2]);int N,K,P,R;
  if(!(in>>N>>K>>P>>R)||N!=64)throw std::runtime_error("bad input header");
  auto bits=[](const std::string&s){U b=0;for(size_t j=0;j<s.size();j++)if(s[j]=='1')b|=U(1)<<j;return b;};
  std::vector<U>A(P),op(K),black(K);std::string s;
  for(auto&x:A){if(!(in>>s)||s.size()!=64)throw std::runtime_error("bad target");x=bits(s);}
  std::vector<int>req(R);for(int&u:req)if(!(in>>u))throw std::runtime_error("missing order");
  for(int k=0;k<K;k++){
   if(!(out>>s)||s.size()!=64)throw std::runtime_error("bad printed paper");
   for(int j=0;j<64;j++){
    if(s[j]!='0'&&s[j]!='1'&&s[j]!='.')throw std::runtime_error("invalid paper character");
    if(s[j]!='.')op[k]|=U(1)<<j;
    if(s[j]=='1')black[k]|=U(1)<<j;
   }
  }
  std::vector<int>order(K);std::iota(order.begin(),order.end(),0);
  long long moves=0;int errors=0,mx=0;
  for(int r=0;r<R;r++){
   int m;if(!(out>>m)||m<0||m>2*K)throw std::runtime_error("invalid move count at order "+std::to_string(r));
   moves+=m;mx=std::max(mx,m);
   for(int i=0;i<m;i++){
    int k,d;if(!(out>>k>>d)||k<0||k>=K||d<0||d>=K)throw std::runtime_error("bad move fields");
    U visible=op[k];auto it=order.begin();while(it!=order.end()&&*it!=k){visible&=~op[*it];++it;}
    if(!visible)throw std::runtime_error("invisible paper at order "+std::to_string(r));
    order.erase(it);order.insert(order.begin()+d,k);
   }
   U seen=0,display=0;for(int k:order){display|=black[k]&~seen;seen|=op[k];}
   errors+=display!=A[req[r]];
  }
  if(out>>s)throw std::runtime_error("extra output");
  std::cout<<"{\"valid\":true,\"moves\":"<<moves<<",\"errors\":"<<errors<<",\"score\":"<<moves+2LL*K*errors<<",\"max_moves\":"<<mx<<"}\n";
  return errors?1:0;
 }catch(const std::exception&e){std::cout<<"{\"valid\":false,\"error\":\""<<e.what()<<"\"}\n";return 2;}
}
