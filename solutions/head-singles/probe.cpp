#include "common.hpp"
int main(int argc,char**argv){
 if(argc<3)return 2;auto base=head::load(argv[1],argv[2]);if(!base)return 3;
 auto old=recover(*base);old->refresh_reset();ProbabilityHead check(*old,2,true);
 std::vector<std::vector<double>>target(P,std::vector<double>(old->H)),donor=target;
 check.all_single_targets(target);check.all_single_donors(donor);double max_error=0;long long different=0;
 for(int a=0;a<P;a++)for(int c=0;c<old->H;c++){
  double x=check.target(a,{a,-1,c}),y=check.donor({a,-1,c});
  different+=(x!=target[a][c])+(y!=donor[a][c]);max_error=std::max({max_error,std::abs(x-target[a][c]),std::abs(y-donor[a][c])});
 }
 assert(max_error<1e-10);int sequences=argc>3?std::stoi(argv[3]):4;std::string name(argv[1]);int seed=std::stoi(name.substr(name.size()-8,4));
 std::array<double,4>seconds{},moves{},model{};std::array<u64,4>hashes{};
 for(int step=0;step<4;step++){
  int mode=(step+seed)%4;ProbabilityHead::fast_single_tables=mode;auto d=*old;double start=elapsed_sec();rematch_probability(d,4,1,2,true,true);seconds[mode]=elapsed_sec()-start;model[mode]=d.cur;
  Solver s=*base;materialize(s,d);s.init_handle_cache();Perforation p(s);p.run(.5,1,false);p.install();
  s.adaptive_initialized=false;s.init_adaptive();s.interleave=std::make_shared<Interleave>();s.interleave->init(s.comparator,s.paper,s.A,s.ded,s.col_of,s.gmask,s.hmask,1e9);s.init_lookahead();
  auto initial=s.save();long long total=0;u64 hash=7819287813ULL;auto add=[&](u64 v){hash^=v+0x9e3779b97f4a7c15ULL+(hash<<6)+(hash>>2);};
  for(int c:d.handle)add(c);for(auto u:d.unit){add(u.a);add(u.b+1);add(u.c);}
  for(int q=0;q<sequences;q++){
   s.restore(initial);std::mt19937_64 rng(331000003ULL*(q+1));int prev=rng()%P;
   for(int t=0;t<1024;t++){
    int u=t?int(rng()%(P-1)):prev;if(t&&u>=prev)u++;prev=u;auto before=s.order;auto path=s.process(u);total+=path.size();assert(s.display()==s.A[u]);
    add(path.size());for(auto[k,depth]:path){add(256*k+depth);int at=std::find(before.begin(),before.end(),k)-before.begin();u64 seen=0;for(int j=0;j<at;j++)seen|=s.paper[before[j]].opaque;assert(s.paper[k].opaque&~seen);before.erase(before.begin()+at);before.insert(before.begin()+depth,k);}assert(before==s.order);for(int k:s.order)add(k);
   }
  }
  assert(!s.plan_failures);hashes[mode]=hash;moves[mode]=double(total)/(1024*sequences);
 }
 std::cout<<std::setprecision(12)<<"[";
 for(int m=0;m<4;m++){
  assert(hashes[m]==hashes[0]);assert(model[m]==model[0]);
  std::cout<<(m?",":"")<<"{\"mode\":"<<m<<",\"moves\":"<<moves[m]<<",\"difference\":"<<moves[m]-moves[0]<<",\"seconds\":"<<seconds[m]<<",\"max_error\":"<<max_error<<",\"different\":"<<different<<"}";
 }
 std::cout<<"]\n";
}
