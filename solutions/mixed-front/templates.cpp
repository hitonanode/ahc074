#include "saved.hpp"
#include <tuple>

struct TemplateSearch {
 Solver&s;u64 hm0,gm;
 struct Pair {int a,b;u64 mask,color,ra,rb;};
 std::vector<Pair>pairs;
 int feasible=0;
 u64 residue(u64 target,u64 required)const{
  for(;;){u64 old=required;for(int k=0;k<6;k++)if(!((s.paper[k].black^target)&s.paper[k].opaque&required))required&=~s.paper[k].opaque;if(required==old)return required;}
 }
 TemplateSearch(Solver&solver):s(solver),hm0(1ULL<<s.handle[0]),gm(s.gmask){
  for(int a=0;a<P;a++)for(int b=a+1;b<P;b++)if(__builtin_popcountll((s.A[a]^s.A[b])&kActiveWindows)<=26){
   u64 mask=(s.A[a]^s.A[b])&(gm|hm0),ra=residue(s.A[a],mask),rb=residue(s.A[b],mask);
   // The two ordinary handle colors are free for the compatibility baseline.
   if(!(ra&gm)&&!(rb&gm))continue;
   pairs.push_back({a,b,mask,s.A[a],ra,rb});
  }
 }
 bool rescue(const Pair&p,u64 op,u64 color)const{
  u64 ca=p.ra&op,cb=p.rb&op;
  bool first=((p.color^color)&ca)==0||((~p.color^color)&ca)==0;
  bool second=((s.A[p.b]^color)&cb)==0||((~s.A[p.b]^color)&cb)==0;
  if(!first||!second)return false;
  return !(residue(p.color,p.ra&~op)|residue(s.A[p.b],p.rb&~op));
 }
 int count(u64 op,u64 color,int own0,int own1,std::vector<std::pair<int,int>>*chosen=nullptr)const{
  int n=0;for(const auto&p:pairs)if(p.a!=own0&&p.a!=own1&&p.b!=own0&&p.b!=own1&&rescue(p,op,color)){n++;if(chosen)chosen->push_back({p.a,p.b});}return n;
 }
};
int main(int argc,char**argv){
 auto ptr=head::load(argv[1],argv[2]);if(!ptr)return 2;auto&s=*ptr;s.comparator.build_tables();TemplateSearch search(s);
 auto start=std::chrono::steady_clock::now();int best=-1,ba=-1,bb=-1;u64 bestmask=0;double bestself=0;
 for(int a=0;a<P;a++)for(int b=a+1;b<P;b++){
  if(!((s.A[a]^s.A[b])&search.hm0))continue;
  u64 op=(s.A[a]^s.A[b])&search.gm;u64 holes=search.gm&~op;
  if(search.residue(s.A[a],holes))continue;
  search.feasible++;op|=search.hm0;int n=search.count(op,s.A[a],a,b);
  if(n>best){best=n;ba=a;bb=b;bestmask=op;bestself=s.comparator.mean_moves(s.A[a],holes)*2/P;}
 }
 std::vector<std::pair<int,int>>chosen;if(ba>=0)search.count(bestmask,s.A[ba],ba,bb,&chosen);
 std::cout<<std::setprecision(12)<<"{\"feasible_templates\":"<<search.feasible<<",\"incompatible\":"<<search.pairs.size()<<",\"rescued\":"<<best<<",\"own\":["<<ba<<","<<bb<<"],\"opaque\":"<<bestmask<<",\"own_extra\":"<<bestself<<",\"seconds\":"<<CLOCK_SCALE*std::chrono::duration<double>(std::chrono::steady_clock::now()-start).count()<<",\"pairs\":[";
 for(int i=0;i<int(chosen.size());i++)std::cout<<(i?",":"")<<"["<<chosen[i].first<<","<<chosen[i].second<<"]";std::cout<<"]}\n";
}
