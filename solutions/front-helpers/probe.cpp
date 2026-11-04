#include "common.hpp"
#include "search.hpp"

int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto d=recover(*base);d->refresh_reset();materialize(*base,*d);
 double begin=elapsed_sec();
 struct Move{int h,f;double delta;};std::vector<Move> moves;
 for(int h=0;h<d->U;h++)if(d->unit[h].c>0)for(int f=0;f<d->U;f++)if(d->unit[f].c==0){
  auto uh=d->unit[h],uf=d->unit[f];
  if(!d->valid(uh,0)||!d->valid(uf,uh.c)||d->color(uh,0)!=d->color(uf,0)||d->color(uf,uh.c)!=d->color(uh,uh.c))continue;
  auto trial=*d;std::swap(trial.unit[h].c,trial.unit[f].c);trial.rebuild();trial.refresh_reset();
  moves.push_back({h,f,trial.cur-d->cur});
 }
 std::sort(moves.begin(),moves.end(),[](auto a,auto b){return a.delta<b.delta;});
 int all_moves=moves.size();if(moves.size()>24)moves.resize(24);
 WeaveSearch::Result choice;std::array<int,4> chosen={-1,-1,-1,-1};
 std::unordered_map<unsigned,double> cache;int tested=0,near=0,rescued=0,replacements=0;
 for(int i=0;i<int(moves.size());i++)for(int j=i+1;j<int(moves.size());j++){
  auto a=moves[i],b=moves[j];if(a.h==b.h||a.f==b.f)continue;
  Solver local=*base;auto trial=*d;std::swap(trial.unit[a.h].c,trial.unit[a.f].c);std::swap(trial.unit[b.h].c,trial.unit[b.f].c);
  trial.rebuild();trial.refresh_reset();materialize(local,trial,false);
  WeaveSearch search(local,trial);search.excluded={a.h,a.f,b.h,b.f};search.helpers={a.h,b.h};search.generic_cache=std::move(cache);
  auto candidate=search.search();cache=std::move(search.generic_cache);tested++;near+=search.near;rescued+=search.rescued;replacements+=search.replacements;
  candidate.delta+=trial.cur-d->cur;
  if(candidate.x>=0&&candidate.delta<choice.delta){choice=candidate;chosen={a.h,a.f,b.h,b.f};}
 }
 double seconds=elapsed_sec()-begin;
 int sequences=argc>3?std::stoi(argv[3]):16;double reference=0;
 std::cout<<std::setprecision(12)<<"{\"relocations\":"<<all_moves<<",\"tested\":"<<tested<<",\"near\":"<<near<<",\"rescued\":"<<rescued<<",\"replacements\":"<<replacements<<",\"model\":"<<(choice.x>=0?choice.delta/P:0)<<",\"design_seconds\":"<<seconds<<",\"x\":"<<choice.x<<",\"a\":"<<(choice.x>=0?choice.unit[0].a:-1)<<",\"b\":"<<(choice.x>=0?choice.unit[0].b:-1)<<",\"ha\":"<<choice.ha<<",\"hb\":"<<choice.hb<<",\"modes\":[";
 for(int mode=0;mode<2;mode++){
  Solver s=*base;auto design=*d;
  if(mode&&choice.x>=0){
   std::swap(design.unit[chosen[0]].c,design.unit[chosen[1]].c);std::swap(design.unit[chosen[2]].c,design.unit[chosen[3]].c);
   design.unit[choice.x]=choice.unit[0];design.unit[choice.y]=choice.unit[1];if(choice.z>=0)design.unit[choice.z]=choice.unit[2];design.rebuild();design.refresh_reset();
   s.forced_helper[choice.unit[0].a]=choice.ha+7;s.forced_helper[choice.unit[0].b]=choice.hb+7;
   materialize(s,design);
   assert(s.helper_required[choice.unit[0].a]&&s.helper_required[choice.unit[0].b]);
   for(int u:{choice.unit[0].a,choice.unit[0].b}){
    bool found=false;for(auto&h:s.interleave->helpers[u])if(h.paper==s.forced_helper[u])found=true;assert(found);
   }
  }
  auto state=s.save();long long total=0,wrong=0,special_total=0,special_count=0;
  for(int q=0;q<sequences;q++){
   s.restore(state);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;
    auto before=s.order;auto path=s.process(u);total+=path.size();wrong+=s.display()!=s.A[u];
    if(choice.x>=0&&(u==choice.unit[0].a||u==choice.unit[0].b))special_total+=path.size(),special_count++;
    if(q==0){
     for(auto[k,depth]:path){int at=std::find(before.begin(),before.end(),k)-before.begin();u64 covered=0;for(int j=0;j<at;j++)covered|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~covered);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}
     assert(before==s.order);
    }
   }
  }
  assert(!wrong);assert(!s.plan_failures);double avg=double(total)/(sequences*1024);if(!mode)reference=avg;
  std::cout<<(mode?",":"")<<"{\"mode\":"<<mode<<",\"moves\":"<<avg<<",\"difference\":"<<avg-reference<<",\"wrong\":"<<wrong<<",\"special_moves\":"<<double(special_total)/std::max(1LL,special_count)<<"}"<<std::flush;
 }
 std::cout<<"]}\n";
}
