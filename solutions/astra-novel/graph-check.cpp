#define main candidate_main
#include "main.cpp"
#undef main
int main(){
 std::mt19937_64 rng(9981);
 long long transitions=0;
 for(int removed=0;removed<=3;removed++){
  Comparator c;c.init(6,36,rng);
  for(auto &e:c.edge) if(e.first==0 && e.second<=removed)e={4,5};
  c.rebuild();c.build_tables();
  int n=c.perms.size();
  for(int a=0;a<n;a++)for(int code=0;code<36;code++){
   int b=c.next[a][code];if(b<0)continue;
   int k=c.perms[a][code/6];u64 cov=0;for(int j=0;j<code/6;j++)cov|=c.opq[c.perms[a][j]];
   assert(c.opq[k]&~cov);assert(c.distance(a,b)==1);transitions++;
  }
  for(int it=0;it<3000;it++){
   int a=rng()%n,b=rng()%n; auto path=c.path(a,b);int cur=a;
   assert(path.size()==size_t(c.distance(a,b)));
   for(auto [k,d]:path){int pos=int(std::find(c.perms[cur].begin(),c.perms[cur].end(),k)-c.perms[cur].begin());int nxt=c.next[cur][pos*6+d];assert(nxt>=0);cur=nxt;}
   assert(cur==b);
  }
 }
 std::cerr<<"verified_generic_transitions = "<<transitions<<"\nverified_generic_paths = 12000\n";
}
