#include "saved.hpp"
struct Experiment {
 Solver& s;std::vector<u64>A;
 struct Entry{double cost=-1;int row=-1,covered=-1;};
 std::array<std::array<Entry,256>,256> costs{};std::vector<int> anchors;
 Experiment(Solver&source):s(source),A(s.A){for(auto&a:A)a&=kActiveWindows;}
 double one(const std::array<unsigned,12>&r)const{u64 key=0;for(int x=0;x<6;x++){if(r[x]>>x&1)return -1;key|=u64(r[x])<<(8*x);}auto&t=PosetSums::get();return t.one[t.slot_of(key)]/720.;}
 void tables(){
  for(int a=0;a<P;a++)for(int b=a+1;b<P;b++){
   auto r=s.comparator.closure(A[a],A[a]^A[b]);double x=one(r);if(x<0)continue;double y=one(s.comparator.closure(A[b],A[a]^A[b]));costs[a][b]=costs[b][a]={(x+y)/2,-1,-1};
  }
  for(int b=0;b<P;b++)if(s.A[b]&kCapBit)for(int row=0;row<6;row++){
   u64 cover=s.paper[row].opaque;if((s.paper[row].black^A[b])&cover)continue;anchors.push_back(b);
   for(int a=0;a<P;a++)if(a!=b){u64 holes=(A[a]^A[b])&~cover;auto ra=s.comparator.closure(A[a],holes),rb=s.comparator.closure(A[b],holes);double x=one(ra);if(x<0)continue;assert(rb[row]==0);rb[row]=63U^(1U<<row);double y=one(rb);assert(y>=0);double cost=(x+y)/2;auto&entry=costs[a][b];if(entry.cost<0||cost<entry.cost-1e-10)entry=costs[b][a]={cost,row,b};}
  }
  std::sort(anchors.begin(),anchors.end());anchors.erase(std::unique(anchors.begin(),anchors.end()),anchors.end());
 }
 void install(Design&d,bool changed)const{
  for(auto&v:d.partners)v.clear();for(auto&r:d.ok)r.fill(0);
  for(int a=0;a<P;a++)for(int b=a+1;b<P;b++){
   double cost=-1;if(changed)cost=costs[a][b].cost;else{auto r=s.comparator.closure(A[a],A[a]^A[b]);double x=one(r);if(x>=0)cost=(x+one(s.comparator.closure(A[b],A[a]^A[b])))/2;}
   if(cost<0)continue;d.ok[a][b]=d.ok[b][a]=1;d.gcost[a][b]=d.gcost[b][a]=cost;d.partners[a].push_back(b);d.partners[b].push_back(a);
  }d.rebuild();
 }
 int climb(Design&d)const{
  using Unit=Design::Unit;int accepted=0;
  for(int iteration=0;iteration<12;iteration++){
   double best=-1e-8;std::vector<int> chosen;std::vector<Unit> replacements;
   auto consider=[&](std::vector<int> ids,std::vector<Unit> units){
    for(auto u:units)if(!d.valid(u,u.c)||(u.b>=0&&!d.ok[u.a][u.b]))return;
    double old=d.cur;for(int x:ids)d.update(d.unit[x],-1);for(auto u:units)d.update(u,1);double delta=d.cur-old;
    for(auto u:units)d.update(u,-1);for(int x:ids)d.update(d.unit[x],1);d.cur=old;
    if(delta<best){best=delta;chosen=std::move(ids);replacements=std::move(units);}
   };
   for(int b:anchors)for(int a=0;a<P;a++)if(a!=b&&d.ok[a][b]){
    int x=d.owner[b],y=d.owner[a];if(x==y)continue;auto ux=d.unit[x],uy=d.unit[y];int otherx=ux.a==b?ux.b:ux.a,othery=uy.a==a?uy.b:uy.a;
    if(otherx<0&&othery<0){
     for(int z=0;z<d.U;z++)if(z!=x&&z!=y&&d.unit[z].b>=0){auto uz=d.unit[z];std::array<int,3> cols{ux.c,uy.c,uz.c};std::array<int,3> perm{0,1,2};do{consider({x,y,z},{{a,b,cols[perm[0]]},{uz.a,-1,cols[perm[1]]},{uz.b,-1,cols[perm[2]]}});}while(std::next_permutation(perm.begin(),perm.end()));}
    }else{
     Unit p{a,b,ux.c},q{otherx<0?othery:otherx,(otherx>=0&&othery>=0)?othery:-1,uy.c};consider({x,y},{p,q});std::swap(p.c,q.c);consider({x,y},{p,q});
    }
   }
   if(chosen.empty())break;for(int i=0;i<int(chosen.size());i++)d.unit[chosen[i]]=replacements[i];d.rebuild();accepted++;
  }return accepted;
 }
};
#ifndef OVERCOAT_NO_MAIN
int main(int argc,char**argv){if(argc<3)return 2;auto source=coat::load(argv[1],argv[2]);if(!source)return 3;auto exp=std::make_unique<Experiment>(*source);exp->tables();
 Design base(exp->A,6,source->G);if(!base.initialize([&](u64 a,u64 b){return source->comparator.compatible(a,b);},[&](u64 a,u64 b){return (exp->one(source->comparator.closure(a,a^b))+exp->one(source->comparator.closure(b,a^b)))/2;},[]{return false;}))return 4;
 // Keep the actual saved pairing and handle order, so the structural comparison
 // starts from exactly the same printed design.
 base.handle=source->handle;for(int a=0;a<P;a++){base.hb[a]=0;for(int j=0;j<base.H;j++)base.hb[a]|=((exp->A[a]>>base.handle[j])&1)<<j;}
 base.unit.clear();for(int k=7;k<K;k++){std::vector<int> owners;for(int u=0;u<P;u++)if(source->ded[u]==k)owners.push_back(u);assert(owners.size()==1||owners.size()==2);base.unit.push_back({owners[0],owners.size()==2?owners[1]:-1,source->col_of[k]});}base.rebuild();double before=base.cur;
 auto control=base,candidate=base;exp->install(control,false);int ca=exp->climb(control);exp->install(candidate,true);int na=exp->climb(candidate);int chosen=0;
 std::cout<<std::setprecision(12)<<"{\"anchors\":"<<exp->anchors.size()<<",\"baseline\":"<<before/256<<",\"control\":"<<control.cur/256<<",\"candidate\":"<<candidate.cur/256<<",\"difference\":"<<(candidate.cur-control.cur)/256<<",\"control_steps\":"<<ca<<",\"candidate_steps\":"<<na<<",\"special\":[";
 for(auto u:candidate.unit)if(u.b>=0&&exp->costs[u.a][u.b].row>=0){auto e=exp->costs[u.a][u.b];std::cout<<(chosen?",":"")<<"["<<u.a<<","<<u.b<<","<<e.row<<","<<e.covered<<"]";chosen++;}
 std::cout<<"],\"selected\":"<<chosen<<"}\n";return 0;}
#endif
