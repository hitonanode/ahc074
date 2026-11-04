#include <algorithm>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <numeric>
#include <random>
#include <set>
#include <string>
#include <vector>
using namespace std; using U=uint64_t;
U bits(const string&s,char c){U x=0;for(int i=0;i<(int)s.size();i++)if(s[i]==c)x|=U(1)<<i;return x;}
int main(int argc,char**argv){
 if(argc>=2&&string(argv[1])=="gen"){
  if(argc!=4){cerr<<"gen seed filename\n";return 2;}mt19937_64 rng(stoull(argv[2]));ofstream o(argv[3]);o<<"64 192 256 1024\n";set<string> seen;
  while(seen.size()<256){string s(32,'0');s+=string(32,'1');shuffle(s.begin(),s.end(),rng);if(seen.insert(s).second)o<<s<<'\n';}
  int prev=-1;for(int i=0;i<1024;i++){int a=uniform_int_distribution<int>(0,i?254:255)(rng);if(i&&a>=prev)a++;o<<a<<'\n';prev=a;}return 0;
 }
 if(argc!=3){cerr<<"judge input output\n";return 2;}
 ifstream in(argv[1]),out(argv[2]);int n,k,p,r;in>>n>>k>>p>>r;vector<U>A(p);string s;for(auto&a:A){in>>s;a=bits(s,'1');}vector<int>req(r);for(auto&a:req)in>>a;
 vector<U>op(k),bl(k);vector<int>ord(k);iota(ord.begin(),ord.end(),0);long long total=0;int errors=0;
 auto fail=[&](string s){cout<<"{\"valid\":false,\"error\":\""<<s<<"\"}\n";return 1;};
 for(int i=0;i<k;i++){if(!(out>>s)||s.size()!=size_t(n)||s.find_first_not_of("01.")!=string::npos)return fail("bad design");op[i]=bits(s,'0')|bits(s,'1');bl[i]=bits(s,'1');}
 for(int q=0;q<r;q++){int m;if(!(out>>m)||m<0||m>2*k)return fail("bad count at request "+to_string(q));total+=m;
  for(int t=0;t<m;t++){int id,d;if(!(out>>id>>d)||id<0||id>=k||d<0||d>=k)return fail("bad move");U covered=0;int at=0;for(;at<k&&ord[at]!=id;at++)covered|=op[ord[at]];if(!(op[id]&~covered))return fail("invisible paper at request "+to_string(q));ord.erase(ord.begin()+at);ord.insert(ord.begin()+d,id);}
  U covered=0,show=0;for(int id:ord){show|=bl[id]&~covered;covered|=op[id];}if(show!=A[req[q]])errors++;
 }
 if(out>>s)return fail("extra output");cout<<"{\"valid\":true,\"moves\":"<<total<<",\"errors\":"<<errors<<",\"score\":"<<total+2LL*k*errors<<"}\n";
}
